import streamlit as st
import requests
import json
import os
import re
from datetime import datetime

# Try to import document processing libraries
try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    from docx import Document as DocxDocument
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

json_folder = r"C:\Users\E0716666\Downloads\mcc door json"

def extract_text_from_pdf(pdf_file):
    """Extract text from uploaded PDF file"""
    if not PDF_AVAILABLE:
        st.error("PDF support not available. Install PyPDF2: pip install PyPDF2")
        return ""
    
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        st.error(f"Error reading PDF: {str(e)}")
        return ""

def extract_text_from_docx(docx_file):
    """Extract text from uploaded DOCX file"""
    if not DOCX_AVAILABLE:
        st.error("DOCX support not available. Install python-docx: pip install python-docx")
        return ""
    
    try:
        doc = DocxDocument(docx_file)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text
    except Exception as e:
        st.error(f"Error reading DOCX: {str(e)}")
        return ""

def extract_text_from_txt(txt_file):
    """Extract text from uploaded TXT file"""
    try:
        return txt_file.read().decode('utf-8')
    except Exception as e:
        st.error(f"Error reading TXT: {str(e)}")
        return ""

def process_uploaded_document(uploaded_file):
    """Process uploaded document and extract text based on file type"""
    if uploaded_file.type == "application/pdf":
        return extract_text_from_pdf(uploaded_file)
    elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return extract_text_from_docx(uploaded_file)
    elif uploaded_file.type == "text/plain":
        return extract_text_from_txt(uploaded_file)
    else:
        st.error(f"Unsupported file type: {uploaded_file.type}")
        return ""

def extract_mcc_info_from_text(text):
    """Extract MCC door parameters from text using pattern matching"""
    info = {}
    text_lower = text.lower()
    
    # Type detection
    if "freedom plus flashgard" in text_lower or "flashgard" in text_lower:
        info["Type"] = "Freedom Plus FlashGard"
        info["Arc Rated"] = True
        info["Door Thickness (Ga)"] = 12
    elif "freedom plus" in text_lower:
        info["Type"] = "Freedom Plus"
        info["Arc Rated"] = False
        info["Door Thickness (Ga)"] = 14
    else:
        info["Type"] = "Freedom Plus"  # Default
        info["Arc Rated"] = False
        info["Door Thickness (Ga)"] = 14
    
    # Door height extraction
    height_patterns = [
        r'door height[:\s]*(\d+)\s*(?:inches?|in|")',
        r'height[:\s]*(\d+)\s*(?:inches?|in|")',
        r'(\d+)\s*(?:inches?|in|")\s*height',
        r'(\d+)\s*(?:inches?|in|")\s*tall'
    ]
    
    for pattern in height_patterns:
        match = re.search(pattern, text_lower)
        if match:
            info["Door Height (inches)"] = int(match.group(1))
            break
    else:
        info["Door Height (inches)"] = 48  # Default
    
    # Bucket type detection
    if "drive bucket" in text_lower or "vfd" in text_lower or "variable frequency" in text_lower:
        info["Bucket Type"] = "Drive Bucket"
    else:
        info["Bucket Type"] = "Starter Bucket"
    
    # Handle type detection
    if "up-down handle" in text_lower or "up down handle" in text_lower:
        info["Handle Type"] = "Up-Down Handle"
    else:
        info["Handle Type"] = "Rotary Handle"  # Default
    
    # Cutouts detection
    cutouts = {}
    
    # RotoTract cutout (only for FlashGard)
    if info["Type"] == "Freedom Plus FlashGard":
        cutouts["RotoTract Cutout"] = True
    else:
        cutouts["RotoTract Cutout"] = False
    
    # Reset cutout (only for drive bucket)
    if info["Bucket Type"] == "Drive Bucket":
        cutouts["Reset Cutout"] = True
    else:
        cutouts["Reset Cutout"] = False
    
    # Fan cutout
    cutouts["Fan Cutout"] = "fan cutout" in text_lower or "cooling fan" in text_lower
    
    # Pemstud
    cutouts["Pemstud"] = "pemstud" in text_lower or "pem stud" in text_lower
    
    # Device panel cutout
    cutouts["Device Panel Cutout"] = ("device panel" in text_lower or 
                                     "control panel" in text_lower or 
                                     "pushbutton" in text_lower or 
                                     "pilot device" in text_lower)
    
    info["Cutouts"] = cutouts
    
    return info


def save_summary_json(summary_dict):
    if not os.path.exists(json_folder):
        os.makedirs(json_folder)
    filename = os.path.join(json_folder, "mcc_door_summary.json")
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(summary_dict, f, indent=4)
    print(f"Summary saved as {filename}")

def save_summary_txt(summary_dict):
    if not os.path.exists(json_folder):
        os.makedirs(json_folder)
    filename = os.path.join(json_folder, "mcc_door_summary.txt")
    with open(filename, "w", encoding="utf-8") as f:
        for key, value in summary_dict.items():
            if isinstance(value, dict):
                f.write(f"{key}:\n")
                for subkey, subval in value.items():
                    f.write(f"  {subkey}: {subval}\n")
            else:
                f.write(f"{key}: {value}\n")
    print(f"Summary saved as {filename}")

def chat_with_llm(messages):
    """Send messages to Ollama and get response"""
    payload = {
        "model": MODEL,
        "messages": messages,
        "stream": False
    }
    try:
        response = requests.post(OLLAMA_URL, json=payload)
        result = response.json()
        return result.get("message", {}).get("content", "")
    except Exception as e:
        return f"Error communicating with Ollama: {str(e)}"

def extract_summary_from_conversation(messages):
    """Extract summary dictionary from conversation"""
    # Extract values from the conversation history (exclude system prompt at index 0)
    conversation = " ".join([msg["content"] for msg in messages[1:]])
    conversation = conversation.lower()
    
    # Determine MCC type and Arc Rating
    type_val = "Freedom Plus FlashGard" if "flashgard" in conversation else "Freedom Plus"
    arc_val = "flashgard" in conversation
    
    # Extract door height (use last match if multiple)
    height_matches = re.findall(r'(\d+)\s*inch', conversation)
    if height_matches:
        height_val = int(height_matches[-1])
    else:
        height_val = 48
    
    # Determine bucket type
    bucket_val = "Drive Bucket" if "drive" in conversation else "Starter Bucket"
    
    # Determine handle type
    handle_val = "Up-Down Handle" if "up-down handle" in conversation or "up down handle" in conversation else "Rotary Handle"
    
    # Determine cutouts
    roto_val = "rototract" in conversation and arc_val
    reset_val = "reset cutout" in conversation or bucket_val == "Drive Bucket"
    fan_val = "fan cutout" in conversation
    pem_val = "pemstud" in conversation
    device_val = "device panel cutout" in conversation
    
    # Set thickness based on arc rating
    thickness_val = 12 if arc_val else 14
    
    # Create the summary dictionary with the extracted values
    summary_dict = {
        "Type": type_val,
        "Arc Rated": arc_val,
        "Door Height (inches)": height_val,
        "Bucket Type": bucket_val,
        "Handle Type": handle_val,
        "Cutouts": {
            "RotoTract Cutout": roto_val,
            "Fan Cutout": fan_val,
            "Pemstud": pem_val,
            "Device Panel Cutout": device_val
        },
        "Door Thickness (Ga)": thickness_val
    }
    
    return summary_dict

def enhanced_streamlit_chat():
    """Enhanced Streamlit chat interface with document context support"""
    st.title("🚪 MCC Door Design Expert")
    st.markdown("Chat with our AI expert to design your Motor Control Center door! Upload documents in the sidebar for additional context.")
    
    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "system", "content": get_initial_prompt()}
        ]
    if "summary_created" not in st.session_state:
        st.session_state.summary_created = False
    if "auto_saved" not in st.session_state:
        st.session_state.auto_saved = False
    
    # Display chat messages (excluding system message)
    for message in st.session_state.messages[1:]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask about MCC door design..."):
        # Check if document context is available and add reminder
        enhanced_prompt = prompt
        if st.session_state.get('document_analysis'):
            doc_info = st.session_state.document_analysis['extracted_info']
            enhanced_prompt = f"""User message: {prompt}

CONTEXT REMINDER: You have access to a processed document with the following MCC door parameters:
{json.dumps(doc_info, indent=2)}

Use this information to answer the user's question. If they're asking about the document or what you found, refer to these extracted parameters."""
        
        # Add user message to chat history (store original prompt for display)
        st.session_state.messages.append({"role": "user", "content": enhanced_prompt})
        with st.chat_message("user"):
            st.markdown(prompt)  # Display original prompt to user
        
        # Get AI response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = chat_with_llm(st.session_state.messages)
                st.markdown(response)
        
        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": response})
        
        # Check if conversation is complete
        completion_indicators = [
            "all info gathered", "i've recorded all the necessary design parameters",
            "i think that's all the questions", "all the necessary information",
            "here is your mcc door summary", "finalize our database",
            "confirmed design parameters", "update our records",
            "here's a summary", "here's a summary of the mcc door design",
            "i'll finalize our database", "parameters will be saved as a json file",
            "saved as a json file", "the parameters will be saved"
        ]
        
        if any(indicator in response.lower() for indicator in completion_indicators):
            st.session_state.summary_created = True
            # Automatically save the JSON when conversation is complete
            if not st.session_state.get("auto_saved", False):
                summary_dict = extract_summary_from_conversation(st.session_state.messages)
                save_summary_json(summary_dict)
                st.session_state.auto_saved = True
                st.success(f"✅ MCC Door parameters automatically saved to: {os.path.join(json_folder, 'mcc_door_summary.json')}")
                st.json(summary_dict)
    
    # Show summary section if conversation is complete
    if st.session_state.summary_created:
        st.divider()
        st.subheader("📋 MCC Door Summary")
        
        if st.button("Generate Summary Dictionary"):
            summary_dict = extract_summary_from_conversation(st.session_state.messages)
            
            # Display the summary
            st.success("Summary dictionary created successfully!")
            st.json(summary_dict)
            
            # Save to file
            save_summary_json(summary_dict)
            st.info(f"Summary saved to: {os.path.join(json_folder, 'mcc_door_summary.json')}")
            
            # Display formatted dictionary
            st.subheader("🔧 Python Dictionary Format")
            dict_string = f"""summary_dict = {{
    "Type": "{summary_dict["Type"]}",
    "Arc Rated": {summary_dict["Arc Rated"]},
    "Door Height (inches)": {summary_dict["Door Height (inches)"]},
    "Bucket Type": "{summary_dict["Bucket Type"]}",
    "Handle Type": "{summary_dict["Handle Type"]}",
    "Cutouts": {{
        "RotoTract Cutout": {summary_dict["Cutouts"]["RotoTract Cutout"]},
        "Fan Cutout": {summary_dict["Cutouts"]["Fan Cutout"]},
        "Pemstud": {summary_dict["Cutouts"]["Pemstud"]},
        "Device Panel Cutout": {summary_dict["Cutouts"]["Device Panel Cutout"]}
    }},
    "Door Thickness (Ga)": {summary_dict["Door Thickness (Ga)"]}
}}"""
            st.code(dict_string, language="python")
        
        if st.button("Start New Conversation"):
            # Reset all session state to clear previous values
            reset_all_session_state()
            # Reinitialize messages
            st.session_state.messages = [
                {"role": "system", "content": get_initial_prompt()}
            ]
            st.session_state.summary_created = False
            st.session_state.auto_saved = False
            st.success("🔄 All data cleared! Starting fresh conversation.")
            st.rerun()
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.1:8b"  # Updated to use Ollama Llama3.1:8b

def get_initial_prompt():
    return (
        "You are an MCC door design expert with document analysis capabilities. MCC stands for Motor Control Center, a centralized assembly used to control multiple electric motors in industrial and commercial settings. "
        "MCCs house motor starters, circuit breakers, overload relays, and other control and protection devices. They are essential for centralized motor control, improved safety and maintenance, scalability, modularity, and energy efficiency via VFDs and PLC integration.\n"
        "IMPORTANT: When users upload documents, you will receive the extracted parameters automatically. Always acknowledge when you have document information available and use it to help design their MCC door. If a user asks about a document they uploaded, confirm that you can see it and reference the extracted parameters.\n"
        "Motor starters are electromechanical devices used to start and stop motors, including contactors for switching, overload relays for protection, and direct-on-line (DOL) or across-the-line configurations.\n"
        "Variable Frequency Drives (VFDs) control motor speed and torque by adjusting the frequency and voltage of the power supply, offering energy savings, soft start/stop, and advanced diagnostics and communication. Drives are used in MCCs for applications requiring precise control, such as conveyors, compressors, and HVAC systems.\n"
        "Freedom Plus MCC: Modular, non-arc-rated motor control center platform. Features include labyrinth vertical bus barrier, universal divider pan and bucket grounding, LED pilot lights, wire marking, and support for VFDs, soft starters, molded case breakers, and power circuit breakers. RotoTract cutout is NOT present in Freedom Plus.\n"
        "Freedom Plus FlashGard MCC: Fully arc-rated MCC with FlashGard arc flash mitigation. Safety features include RotoTractE retractable stab mechanism, visual indicators for stab and shutter positions, automatic shutters, and remote racking via pendant station. RotoTract cutout is present in FlashGard.\n"
        "Door size is always in inches. For arc and non-arc types: Arc type → thickness 12 Ga; non-arc → thickness 14 Ga. You should record this thickness information as part of the design parameters.\n"
        "You must also extract information about cutouts needed on the door:\n"
        "- If the user confirms Freedom Plus FlashGard, RotoTract is one of the cutouts. Save this info. For Freedom Plus, RotoTract is NOT present.\n"
        "- If the user selects drive bucket, add reset cutout as one of the cutouts. Reset cutout is NOT present for starter bucket.\n"
        "- Ask separately: 'Is a fan cutout needed?' Please respond with 'fan cutout' or 'none'.\n"
        "- Ask separately: 'Is a pemstud needed?' Please respond with 'pemstud' or 'none'.\n"
        "- Ask separately: 'Is a device panel cutout needed?' A device panel cutout is a pre-punched opening designed to mount pilot devices such as pushbuttons, selector switches, indicator lights, and meters. Please respond with 'device panel cutout' or 'none'.\n"
        "Engage the user in a conversation to extract the following design parameters required to build an MCC door:\n"
        "1. Is it Freedom Plus (non arc rated) or Freedom Plus Flashgard (arc rated) type MCC?\n"
        "2. What is the door height (in inches)?\n"
        "3. Is it a drive bucket or starter bucket?\n"
        "4. Do they want an up-down handle or rotary handle?\n"
        "5. Confirm cutout requirements: RotoTract (if FlashGard), reset cutout (if drive bucket), fan cutout (ask separately), pemstud (ask separately), device panel cutout (ask separately).\n"
        "Ask these questions one by one, confirm each answer before moving to the next, and record all design and cutout parameters in your database.\n"
        "Once you have collected all the necessary design parameters, simply inform the user that 'I've recorded all the necessary design parameters for your MCC door. The parameters will be saved as a JSON file.' Do NOT ask about cost, lead time, or manufacturing calculations."
    )

def display_summary(summary_dict):
    print("\nLet's start building the MCC door! Here are your selected parameters:")
    print(json.dumps(summary_dict, indent=4))

def extract_info_from_txt(file_path):
    """
    Extract MCC door design parameters from a text file
    More robust implementation with better pattern matching and error handling
    """
    info = {}
    
    # Check if file exists
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return info
        
    try:
        # Read file with error handling
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            text = f.read().lower()
            
        # Log the extraction attempt
        print(f"Extracting info from: {file_path} (length: {len(text)} chars)")
        
        # Use regular expressions for more robust matching
        import re
        
        # Type detection with variations
        type_patterns = [
            # Direct mentions with colon
            r'(?:type|door type|mcc type)\s*:?\s*(freedom\s+plus\s+flashgard)',
            r'(?:type|door type|mcc type)\s*:?\s*(freedom\s+plus)',
            # Just the type names
            r'(freedom\s+plus\s+flashgard)',
            r'(freedom\s+plus)(?!\s+flashgard)',  # Freedom Plus but not FlashGard
        ]
        
        # Try each pattern in order
        type_value = None
        print(f"Debug: Looking for type in text: {text[:200]}...")
        for i, pattern in enumerate(type_patterns):
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                print(f"Debug: Pattern {i} matched: {match.group(1)}")
                matched_text = match.group(1).lower()
                if 'flashgard' in matched_text:
                    type_value = 'Freedom Plus FlashGard'
                else:
                    type_value = 'Freedom Plus'
                break
        
        print(f"Debug: Final type_value: {type_value}")
        info['Type'] = type_value
        info['Arc Rated'] = True if type_value == 'Freedom Plus FlashGard' else (False if type_value == 'Freedom Plus' else None)
        
        # Door height with multiple patterns
        height_patterns = [
            r'(?:door\s+height|height)\s*:?\s*(\d+)\s*(?:inch|inches|in|")',
            r'(?:door\s+height|height)\s*:?\s*(\d+)',
            r'(\d+)\s*(?:inch|inches|in|")',
        ]
        
        height_value = None
        print(f"Debug: Looking for height in text...")
        for i, pattern in enumerate(height_patterns):
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    height_value = int(match.group(1))
                    print(f"Debug: Height pattern {i} matched: {height_value}")
                    break
                except ValueError:
                    continue
        
        print(f"Debug: Final height_value: {height_value}")
        info['Door Height (inches)'] = height_value
        
        # Bucket type detection
        bucket_patterns = [
            r'(?:bucket\s+type|bucket)\s*:?\s*(drive\s*bucket)',
            r'(?:bucket\s+type|bucket)\s*:?\s*(starter\s*bucket)',
            r'(drive\s*bucket)',
            r'(starter\s*bucket)'
        ]
        
        bucket_value = None
        print(f"Debug: Looking for bucket type...")
        for i, pattern in enumerate(bucket_patterns):
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                matched_text = match.group(1).lower()
                if 'drive' in matched_text:
                    bucket_value = 'Drive Bucket'
                else:
                    bucket_value = 'Starter Bucket'
                print(f"Debug: Bucket pattern {i} matched: {bucket_value}")
                break
        
        print(f"Debug: Final bucket_value: {bucket_value}")
        info['Bucket Type'] = bucket_value
        
        # Handle type detection
        handle_patterns = [
            r'(?:handle\s+type|handle)\s*:?\s*(up[-\s]down\s*handle)',
            r'(?:handle\s+type|handle)\s*:?\s*(rotary\s*handle)',
            r'(up[-\s]down\s*handle)',
            r'(rotary\s*handle)'
        ]
        
        handle_value = None
        print(f"Debug: Looking for handle type...")
        for i, pattern in enumerate(handle_patterns):
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                matched_text = match.group(1).lower()
                if 'up' in matched_text and 'down' in matched_text:
                    handle_value = 'Up-Down Handle'
                elif 'rotary' in matched_text:
                    handle_value = 'Rotary Handle'
                print(f"Debug: Handle pattern {i} matched: {handle_value}")
                break
        
        print(f"Debug: Final handle_value: {handle_value}")
        info['Handle Type'] = handle_value
        
        # Cutouts with more detailed pattern matching
        cutouts = {}
        
        # RotoTract Cutout
        cutouts['RotoTract Cutout'] = any(pattern in text for pattern in [
            'rototract cutout',
            'roto tract cutout',
            'rototract: yes',
            'rototract:yes',
            'rototract: true',
            'with rototract'
        ])
        
        # Fan Cutout
        cutouts['Fan Cutout'] = any(pattern in text for pattern in [
            'fan cutout',
            'fan: yes',
            'fan:yes',
            'fan: true',
            'with fan',
            'needs fan'
        ])
        
        # Pemstud
        cutouts['Pemstud'] = any(pattern in text for pattern in [
            'pemstud',
            'pem stud',
            'pemstud: yes',
            'pemstud:yes',
            'pemstud: true',
            'with pemstud'
        ])
        
        # Device Panel Cutout
        cutouts['Device Panel Cutout'] = any(pattern in text for pattern in [
            'device panel cutout',
            'device panel: yes',
            'device panel:yes',
            'device panel: true',
            'with device panel',
            'needs device panel'
        ])
        
        info['Cutouts'] = cutouts
        
        # Door thickness based on arc rating
        if info.get('Arc Rated') is not None:
            info['Door Thickness (Ga)'] = 12 if info['Arc Rated'] else 14
        else:
            # Try to determine thickness directly
            thickness_patterns = [
                r'(?:door thickness|thickness)\s*:?\s*(\d+)\s*(?:ga|gauge)',
                r'(\d+)\s*(?:ga|gauge)\s*(?:door|thickness)'
            ]
            
            thickness_value = None
            for pattern in thickness_patterns:
                match = re.search(pattern, text)
                if match:
                    try:
                        thickness_value = int(match.group(1))
                        break
                    except ValueError:
                        continue
                        
            info['Door Thickness (Ga)'] = thickness_value
            
        # Log the extracted information
        print(f"Extracted info: {info}")
        
        return info
        
    except Exception as e:
        import traceback
        print(f"Error extracting info from {file_path}: {e}")
        print(traceback.format_exc())
        return {}

def prompt_missing_fields(info):
    fields = [
        ('Type', "Is it Freedom Plus (non arc rated) or Freedom Plus Flashgard (arc rated) type MCC?"),
        ('Door Height (inches)', "What is the door height (in inches)?"),
        ('Bucket Type', "Is it a drive bucket or starter bucket?"),
        ('Handle Type', "Do you want an up-down handle or rotary handle?"),
    ]
    cutout_fields = [
        ('RotoTract Cutout', "Is RotoTract cutout needed? (yes/no)"),
        ('Fan Cutout', "Is a fan cutout needed? (yes/no)"),
        ('Pemstud', "Is a pemstud needed? (yes/no)"),
        ('Device Panel Cutout', "Is a device panel cutout needed? (yes/no)"),
    ]
    # Main fields
    for key, question in fields:
        if info.get(key) is None:
            val = input(question + " ")
            if key == 'Type':
                info[key] = val if val else None
                info['Arc Rated'] = True if 'flashgard' in val.lower() else False
            elif key == 'Door Height (inches)':
                try:
                    info[key] = int(val)
                except:
                    info[key] = None
            else:
                info[key] = val if val else None
    # Cutouts
    if 'Cutouts' not in info:
        info['Cutouts'] = {}
    for key, question in cutout_fields:
        if info['Cutouts'].get(key) is None:
            val = input(question + " ")
            info['Cutouts'][key] = val.strip().lower() == 'yes'
    # Door thickness
    if info.get('Arc Rated') is not None:
        info['Door Thickness (Ga)'] = 12 if info['Arc Rated'] else 14
    else:
        info['Door Thickness (Ga)'] = None
    return info

def reset_all_session_state():
    """Reset all session state values to clear previous data"""
    keys_to_reset = [
        "document_analysis",
        "document_processed", 
        "last_uploaded_file",
        "messages",
        "summary_created",
        "auto_saved",
        "extracted_parameters"
    ]
    
    for key in keys_to_reset:
        if key in st.session_state:
            del st.session_state[key]
    
    # Reinitialize essential session state
    st.session_state.document_analysis = None
    st.session_state.document_processed = False

def main():
    """Main function for Streamlit app"""
    st.set_page_config(
        page_title="MCC Door Design Expert",
        page_icon="🚪",
        layout="centered"  # Default: wide mode unchecked
    )
    
    # Initialize session state for document analysis
    if "document_analysis" not in st.session_state:
        st.session_state.document_analysis = None
    if "document_processed" not in st.session_state:
        st.session_state.document_processed = False
    
    # Sidebar for document upload
    st.sidebar.title("� Document Upload")
    st.sidebar.markdown("Upload documents containing MCC door specifications:")
    
    # File uploader in sidebar
    uploaded_file = st.sidebar.file_uploader(
        "Choose a file",
        type=['pdf', 'docx', 'txt'],
        help="Supported formats: PDF, DOCX, TXT"
    )
    
    # Process uploaded document
    if uploaded_file is not None:
        if not st.session_state.document_processed or st.session_state.get("last_uploaded_file") != uploaded_file.name:
            with st.spinner(f"Processing {uploaded_file.name}..."):
                # Extract text from document
                extracted_text = process_uploaded_document(uploaded_file)
                
                if extracted_text:
                    # Extract MCC parameters from text
                    document_info = extract_mcc_info_from_text(extracted_text)
                    
                    # Store in session state
                    st.session_state.document_analysis = {
                        "filename": uploaded_file.name,
                        "text_length": len(extracted_text),
                        "extracted_info": document_info,
                        "raw_text": extracted_text[:1000] + "..." if len(extracted_text) > 1000 else extracted_text
                    }
                    st.session_state.document_processed = True
                    st.session_state.last_uploaded_file = uploaded_file.name
                    
                    # Automatically add document context to chat
                    doc_context = f"""
IMPORTANT: A document has been uploaded and processed automatically.

Document Details:
- Filename: {uploaded_file.name}
- Content length: {len(extracted_text)} characters

Extracted MCC Door Parameters:
{json.dumps(document_info, indent=2)}

Raw document content (first 500 chars):
{extracted_text[:500]}...

You now have access to this document information. When the user asks about the document or mentions uploading it, acknowledge that you can see the document and use the extracted parameters to help them design their MCC door. If any parameters are missing or unclear from the document, ask for clarification.
"""
                    
                    # Initialize messages if not exists
                    if "messages" not in st.session_state:
                        st.session_state.messages = [
                            {"role": "system", "content": get_initial_prompt()}
                        ]
                    
                    # Add document context as system message
                    st.session_state.messages.append({
                        "role": "system", 
                        "content": doc_context
                    })
                    
                    st.sidebar.success(f"✅ {uploaded_file.name} processed and added to chat context!")
                else:
                    st.sidebar.error("Failed to extract text from document")
    else:
        # If no file is uploaded (user deleted/cleared the document)
        if st.session_state.document_processed:
            st.sidebar.info("📝 Document removed. Previous data cleared.")
            st.session_state.document_analysis = None
            st.session_state.document_processed = False
            if "last_uploaded_file" in st.session_state:
                del st.session_state.last_uploaded_file
    
    # Display document analysis in sidebar
    if st.session_state.document_analysis:
        st.sidebar.subheader("📋 Document Analysis")
        analysis = st.session_state.document_analysis
        
        st.sidebar.text(f"File: {analysis['filename']}")
        st.sidebar.text(f"Text length: {analysis['text_length']} characters")
        
        # Show extracted parameters
        with st.sidebar.expander("📊 Extracted Parameters"):
            st.json(analysis['extracted_info'])
        
        # Show preview of text
        with st.sidebar.expander("📄 Text Preview"):
            st.text_area("Document content preview:", analysis['raw_text'], height=100, disabled=True)
        
        # Clear buttons
        col1, col2 = st.sidebar.columns(2)
        with col1:
            if st.button("🗑️ Clear Document", key="clear_doc"):
                st.session_state.document_analysis = None
                st.session_state.document_processed = False
                if "last_uploaded_file" in st.session_state:
                    del st.session_state.last_uploaded_file
                st.sidebar.success("Document cleared!")
                st.rerun()
        
        with col2:
            if st.button("🔄 Reset All", key="reset_all"):
                reset_all_session_state()
                st.sidebar.success("All data cleared!")
                st.rerun()
        
        # Option to use document parameters
        if st.sidebar.button("🔄 Use Document Parameters in Chat"):
            # Create a system message with document context
            doc_context = f"""
            Document Analysis Available:
            Filename: {analysis['filename']}
            
            Extracted MCC Door Parameters:
            {json.dumps(analysis['extracted_info'], indent=2)}
            
            Use this information to assist the user with their MCC door design. If the document contains 
            all necessary parameters, you can create the final summary. If some parameters are missing 
            or unclear, ask the user for clarification.
            """
            
            # Add document context to chat messages
            if "messages" not in st.session_state:
                st.session_state.messages = [
                    {"role": "system", "content": get_initial_prompt()}
                ]
            
            # Add document context as a system message
            st.session_state.messages.append({
                "role": "system", 
                "content": doc_context
            })
            
            # Add a user message to trigger response
            st.session_state.messages.append({
                "role": "user", 
                "content": f"I've uploaded a document ({analysis['filename']}) with MCC door specifications. Please analyze the extracted parameters and help me complete the design."
            })
            
            st.sidebar.success("Document parameters added to chat context!")
    
    # Add a general reset button at the bottom of sidebar if no document is uploaded
    if not st.session_state.document_analysis:
        st.sidebar.divider()
        if st.sidebar.button("🔄 Reset All Data", key="reset_all_general"):
            reset_all_session_state()
            st.sidebar.success("All chat and session data cleared!")
            st.rerun()
    
    # Main chat interface
    enhanced_streamlit_chat()

if __name__ == "__main__":
    main()
