from fastapi import FastAPI, Request, Form, File, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os
import json
import re
from datetime import datetime
from typing import List, Optional
from dotenv import load_dotenv
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse
import google.generativeai as genai
from openai import OpenAI
from pathlib import Path

# Load environment variables
load_dotenv()

app = FastAPI()

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Function to strip ANSI codes from text
def strip_ansi_codes(text: str) -> str:
    """Remove ANSI escape codes from text"""
    import re
    # Remove ANSI escape sequences
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', str(text))

# Jinja2 filter will be registered after clean_error_message is defined

# Initialize Twilio client
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

twilio_client = None
if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
    twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Initialize AI (prefer Gemini, fallback to OpenAI)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

openai_client = None
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    ai_model = genai.GenerativeModel('gemini-pro')
    ai_provider = "gemini"
elif OPENAI_API_KEY:
    openai_client = OpenAI(api_key=OPENAI_API_KEY)
    ai_provider = "openai"
else:
    ai_provider = None

# Call logs file
CALLS_JSON = "calls.json"

def load_call_logs():
    """Load call logs from JSON file"""
    if os.path.exists(CALLS_JSON):
        with open(CALLS_JSON, 'r') as f:
            try:
                return json.load(f)
            except:
                return []
    return []

def save_call_log(call_data):
    """Save a call log entry"""
    logs = load_call_logs()
    logs.append(call_data)
    with open(CALLS_JSON, 'w') as f:
        json.dump(logs, f, indent=2)

def clean_error_message(error_text):
    """Clean error message by removing ANSI codes and extracting core message"""
    if not error_text:
        return error_text
    
    # First strip ANSI codes
    cleaned = strip_ansi_codes(str(error_text))
    
    # If it's a verbose Twilio error, extract just the core message
    if "Twilio returned the following information:" in cleaned:
        parts = cleaned.split("Twilio returned the following information:")
        if len(parts) > 1:
            error_msg = parts[1].strip()
            # Remove any remaining ANSI-like codes
            error_msg = re.sub(r'\[[0-9;]*m', '', error_msg)
            # Remove "More information may be available here" and URL
            error_msg = re.sub(r'More information may be available here:.*$', '', error_msg, flags=re.DOTALL)
            error_msg = error_msg.strip()
            # Remove URL if present
            error_msg = re.sub(r'https?://[^\s]+$', '', error_msg).strip()
            return error_msg
    
    # Also handle cases where error starts with "HTTP Error" but has the core message
    if "HTTP Error" in cleaned and "Unable to create record:" in cleaned:
        # Extract the complete error message starting from "Unable to create record:"
        match = re.search(r'Unable to create record:.*?(?=More information may be available|$)', cleaned, re.DOTALL)
        if match:
            error_msg = match.group(0).strip()
            # Clean up any extra whitespace
            error_msg = re.sub(r'\s+', ' ', error_msg)
            return error_msg
    
    return cleaned

def cleanup_all_logs():
    """Clean up all error messages in existing logs"""
    logs = load_call_logs()
    cleaned_logs = []
    for log in logs:
        if 'error' in log and log['error']:
            log['error'] = clean_error_message(log['error'])
        cleaned_logs.append(log)
    
    # Save cleaned logs
    with open(CALLS_JSON, 'w') as f:
        json.dump(cleaned_logs, f, indent=2)
    
    return len(cleaned_logs)

# Register Jinja2 filter for cleaning ANSI codes (after clean_error_message is defined)
def clean_ansi(text):
    """Jinja2 filter to remove ANSI codes and extract core error messages"""
    return clean_error_message(text)

templates.env.filters["clean_ansi"] = clean_ansi

def get_verified_numbers():
    """Get list of verified phone numbers from Twilio"""
    verified_numbers = []
    if twilio_client:
        try:
            verified_list = twilio_client.outgoing_caller_ids.list()
            verified_numbers = [str(v.phone_number) for v in verified_list]
        except:
            pass
    return verified_numbers

def parse_phone_numbers(text: str) -> List[str]:
    """Parse phone numbers from text (comma or newline separated) and format to E.164"""
    # Get verified numbers to help with country code detection
    verified_numbers = get_verified_numbers()
    verified_digits = {}
    for v in verified_numbers:
        # Normalize: remove all non-digits except +
        digits = re.sub(r'[^\d+]', '', v)
        # Store mapping of last 10 digits to full number
        if len(digits) >= 10:
            last_10 = digits[-10:]
            verified_digits[last_10] = v.replace(' ', '').replace('-', '')
    
    # Remove whitespace and split by comma or newline
    numbers = re.split(r'[,\n\r]+', text)
    # Clean and filter valid numbers
    cleaned = []
    for num in numbers:
        # Remove all non-digit characters except +
        num_clean = re.sub(r'[^\d+]', '', num.strip())
        
        if not num_clean:
            continue
        
        original_num = num_clean
        
        # If number doesn't start with +, try to determine country code
        if not num_clean.startswith('+'):
            # Check if this matches a verified number (last 10 digits)
            if len(num_clean) == 10:
                if num_clean in verified_digits:
                    # Use the verified number's format
                    num_clean = verified_digits[num_clean]
                else:
                    # Default to US/Canada for 10-digit numbers
                    num_clean = '+1' + num_clean
            # If it's 11 digits and starts with 1, add +
            elif len(num_clean) == 11 and num_clean.startswith('1'):
                num_clean = '+' + num_clean
            # For Indian numbers: 10 digits starting with 9 (common pattern)
            elif len(num_clean) == 10 and num_clean.startswith('9'):
                # Check if it matches a verified number
                if num_clean in verified_digits:
                    num_clean = verified_digits[num_clean]
                else:
                    # Try +91 for India (most common)
                    num_clean = '+91' + num_clean
            # For other lengths, add + prefix
            else:
                num_clean = '+' + num_clean
        
        # Validate: should be at least 10 digits after country code
        digits_only = re.sub(r'[^\d]', '', num_clean)
        if len(digits_only) >= 10:
            cleaned.append(num_clean)
    
    return cleaned

def parse_ai_command(prompt: str) -> dict:
    """Parse AI command using Gemini or OpenAI"""
    if not ai_provider:
        # Fallback to simple regex parsing
        if "call" in prompt.lower() and any(char.isdigit() for char in prompt):
            numbers = re.findall(r'\d{10,}', prompt)
            if numbers:
                return {"action": "call_single", "number": numbers[0]}
        if "start calling" in prompt.lower() or "call all" in prompt.lower():
            return {"action": "call_all"}
        return {"action": "unknown", "error": "Could not parse command"}
    
    system_prompt = """You are a command parser for a DialAI app. 
Parse the user's command and return a JSON object with the action and parameters.

Possible actions:
- "call_single": Call a single phone number
- "call_all": Start calling all numbers in the list
- "unknown": If the command is unclear

Examples:
User: "Call 9876543210"
Response: {"action": "call_single", "number": "9876543210"}

User: "Start calling all numbers"
Response: {"action": "call_all"}

User: "Make a call to 1800123456"
Response: {"action": "call_single", "number": "1800123456"}

Return ONLY valid JSON, no other text."""
    
    try:
        if ai_provider == "gemini":
            full_prompt = f"{system_prompt}\n\nUser command: {prompt}\n\nResponse:"
            response = ai_model.generate_content(full_prompt)
            result_text = response.text.strip()
            # Extract JSON from response
            json_match = re.search(r'\{[^}]+\}', result_text)
            if json_match:
                return json.loads(json_match.group())
        elif ai_provider == "openai" and openai_client:
            response = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            result_text = response.choices[0].message.content.strip()
            json_match = re.search(r'\{[^}]+\}', result_text)
            if json_match:
                return json.loads(json_match.group())
    except Exception as e:
        print(f"AI parsing error: {e}")
    
    # Fallback to regex
    if "call" in prompt.lower():
        numbers = re.findall(r'\d{10,}', prompt)
        if numbers:
            return {"action": "call_single", "number": numbers[0]}
    if "start calling" in prompt.lower() or "call all" in prompt.lower():
        return {"action": "call_all"}
    
    return {"action": "unknown", "error": "Could not parse command"}

def make_twilio_call(phone_number: str) -> dict:
    """Make a call using Twilio API"""
    if not twilio_client:
        return {
            "success": False,
            "error": "Twilio credentials not configured"
        }
    
    try:
        # Create TwiML response
        response = VoiceResponse()
        # Customize the message here - this is what the receiver will hear
        message = os.getenv("CALL_MESSAGE", "Hello, this is a test call from the DialAI app.")
        voice = os.getenv("CALL_VOICE", "alice")  # Options: alice, man, woman, polly.*
        language = os.getenv("CALL_LANGUAGE", "en")  # Language code
        
        response.say(message, voice=voice, language=language)
        
        # Make the call
        call = twilio_client.calls.create(
            to=phone_number,
            from_=TWILIO_PHONE_NUMBER,
            twiml=str(response)
        )
        
        return {
            "success": True,
            "call_sid": call.sid,
            "status": call.status,
            "number": phone_number
        }
    except Exception as e:
        # Clean error message by removing ANSI codes
        error_msg = strip_ansi_codes(str(e))
        
        # Extract the actual error message if it's a Twilio error
        if "Twilio returned the following information:" in error_msg:
            # Try to extract the main error message
            parts = error_msg.split("Twilio returned the following information:")
            if len(parts) > 1:
                error_msg = parts[1].strip()
                # Remove any remaining ANSI-like codes and extra text
                error_msg = re.sub(r'\[[0-9;]*m', '', error_msg)  # Remove ANSI codes
                error_msg = re.sub(r'More information may be available here:.*$', '', error_msg, flags=re.DOTALL)
                error_msg = error_msg.strip()
                # If there's a URL at the end, remove it
                error_msg = re.sub(r'https?://[^\s]+$', '', error_msg).strip()
        
        # Add helpful guidance for common errors
        if "not yet verified" in error_msg.lower() or "unverified" in error_msg.lower() or "verified" in error_msg.lower():
            if "source phone number" in error_msg.lower():
                error_msg += " | Fix: Use a Twilio-purchased number in TWILIO_PHONE_NUMBER (Twilio numbers are auto-verified)"
            else:
                # This is about the destination number (the number you're trying to call)
                number_match = re.search(r'\+?\d{10,}', error_msg)
                if number_match:
                    unverified_num = number_match.group(0)
                    error_msg += f" | Action Required: Verify the DESTINATION number {unverified_num} at https://console.twilio.com/us1/develop/phone-numbers/manage/verified (Trial accounts must verify numbers they want to CALL)"
                else:
                    error_msg += " | Tip: For trial accounts, verify destination numbers in Twilio Console → Verified Caller IDs"
        
        return {
            "success": False,
            "error": error_msg,
            "number": phone_number
        }

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page with phone number input and AI command"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/logs", response_class=HTMLResponse)
async def logs_page(request: Request):
    """Display call logs page"""
    logs = load_call_logs()
    return templates.TemplateResponse("logs.html", {"request": request, "logs": logs})

@app.post("/call")
async def initiate_calls(
    numbers: str = Form(None),
    file: UploadFile = File(None)
):
    """Initiate calls for given phone numbers"""
    phone_numbers = []
    
    # Parse from form or file
    if file and file.filename:
        content = await file.read()
        text = content.decode('utf-8')
        phone_numbers = parse_phone_numbers(text)
    elif numbers:
        phone_numbers = parse_phone_numbers(numbers)
    
    if not phone_numbers:
        return JSONResponse({
            "success": False,
            "error": "No valid phone numbers provided"
        })
    
    results = []
    for number in phone_numbers:
        result = make_twilio_call(number)
        call_log = {
            "number": number,
            "status": result.get("status", "failed"),
            "success": result.get("success", False),
            "timestamp": datetime.now().isoformat(),
            "call_sid": result.get("call_sid"),
            "error": result.get("error")
        }
        save_call_log(call_log)
        results.append(call_log)
    
    return JSONResponse({
        "success": True,
        "total": len(phone_numbers),
        "results": results
    })

@app.post("/ai-command")
async def handle_ai_command(
    command: str = Form(...),
    numbers: str = Form(None)
):
    """Handle AI-based commands"""
    parsed = parse_ai_command(command)
    
    if parsed["action"] == "call_single":
        number = parsed.get("number")
        if number:
            result = make_twilio_call(number)
            call_log = {
                "number": number,
                "status": result.get("status", "failed"),
                "success": result.get("success", False),
                "timestamp": datetime.now().isoformat(),
                "call_sid": result.get("call_sid"),
                "error": result.get("error")
            }
            save_call_log(call_log)
            return JSONResponse({
                "success": True,
                "action": "call_single",
                "result": call_log
            })
        else:
            return JSONResponse({
                "success": False,
                "error": "No phone number found in command"
            })
    
    elif parsed["action"] == "call_all":
        if not numbers:
            return JSONResponse({
                "success": False,
                "error": "No phone numbers available to call"
            })
        
        phone_numbers = parse_phone_numbers(numbers)
        if not phone_numbers:
            return JSONResponse({
                "success": False,
                "error": "No valid phone numbers found"
            })
        
        results = []
        for number in phone_numbers:
            result = make_twilio_call(number)
            call_log = {
                "number": number,
                "status": result.get("status", "failed"),
                "success": result.get("success", False),
                "timestamp": datetime.now().isoformat(),
                "call_sid": result.get("call_sid"),
                "error": result.get("error")
            }
            save_call_log(call_log)
            results.append(call_log)
        
        return JSONResponse({
            "success": True,
            "action": "call_all",
            "total": len(phone_numbers),
            "results": results
        })
    
    else:
        return JSONResponse({
            "success": False,
            "error": parsed.get("error", "Unknown command"),
            "parsed": parsed
        })

@app.get("/api/logs")
async def get_logs():
    """API endpoint to get call logs"""
    logs = load_call_logs()
    return JSONResponse({"logs": logs})

@app.post("/api/cleanup-logs")
async def cleanup_logs_endpoint():
    """API endpoint to clean up all error messages in logs"""
    try:
        count = cleanup_all_logs()
        return JSONResponse({
            "success": True,
            "message": f"Cleaned up {count} log entries",
            "count": count
        })
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)

@app.get("/api/check-verification/{phone_number}")
async def check_verification(phone_number: str):
    """Check if a phone number is verified in Twilio"""
    if not twilio_client:
        return JSONResponse({
            "success": False,
            "error": "Twilio credentials not configured"
        })
    
    try:
        # Clean the phone number
        cleaned_number = phone_number.strip()
        if not cleaned_number.startswith('+'):
            if len(cleaned_number) == 10:
                cleaned_number = '+1' + cleaned_number
            elif len(cleaned_number) == 11 and cleaned_number.startswith('1'):
                cleaned_number = '+' + cleaned_number
        
        # Try to fetch verified caller IDs
        verified_numbers = twilio_client.outgoing_caller_ids.list()
        verified_phone_numbers = [str(v.phone_number) for v in verified_numbers]
        
        # Normalize for comparison (remove spaces, dashes, etc.)
        normalized_verified = [re.sub(r'[^\d+]', '', v) for v in verified_phone_numbers]
        normalized_check = re.sub(r'[^\d+]', '', cleaned_number)
        
        is_verified = normalized_check in normalized_verified
        
        return JSONResponse({
            "success": True,
            "phone_number": cleaned_number,
            "is_verified": is_verified,
            "verified_numbers": verified_phone_numbers,
            "message": "Verified" if is_verified else f"Number {cleaned_number} is NOT verified. Please verify it in Twilio Console."
        })
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e),
            "phone_number": phone_number
        }, status_code=500)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

