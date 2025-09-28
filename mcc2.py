import streamlit as st
import requests
import json
import os
import re
from datetime import datetime

json_folder = r"C:\Users\E0716666\Downloads\mcc door json"


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

def streamlit_chat():
    """Streamlit-based chat interface"""
    st.title("🚪 MCC Door Design Expert")
    st.markdown("Chat with our AI expert to design your Motor Control Center door!")
    
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
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
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
            st.session_state.messages = [
                {"role": "system", "content": get_initial_prompt()}
            ]
            st.session_state.summary_created = False
            st.session_state.auto_saved = False
            st.rerun()
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.1:8b"  # Updated to use Ollama Llama3.1:8b

def get_initial_prompt():
    return (
        "You are an MCC door design expert. MCC stands for Motor Control Center, a centralized assembly used to control multiple electric motors in industrial and commercial settings. "
        "MCCs house motor starters, circuit breakers, overload relays, and other control and protection devices. They are essential for centralized motor control, improved safety and maintenance, scalability, modularity, and energy efficiency via VFDs and PLC integration.\n"
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

def main():
    """Main function for Streamlit app"""
    st.set_page_config(
        page_title="MCC Door Design Expert",
        page_icon="🚪",
        layout="wide"
    )
    
    # Sidebar for mode selection
    st.sidebar.title("🔧 MCC Door Design")
    mode = st.sidebar.selectbox(
        "Choose input method:",
        ["Chat with AI Expert", "Upload Document"]
    )
    
    if mode == "Upload Document":
        st.title("📄 Document-based MCC Door Design")
        st.markdown("Upload a text document containing your MCC door requirements.")
        
        uploaded_file = st.file_uploader("Choose a text file", type=['txt'])
        
        if uploaded_file is not None:
            # Save uploaded file temporarily
            temp_path = os.path.join(json_folder, "temp_upload.txt")
            if not os.path.exists(json_folder):
                os.makedirs(json_folder)
            
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getvalue())
            
            # Extract information
            info = extract_info_from_txt(temp_path)
            
            st.subheader("📋 Extracted Information")
            st.json(info)
            
            # Create summary dictionary
            summary_dict = {
                "Type": info.get("Type", "Freedom Plus"),
                "Arc Rated": info.get("Arc Rated", False),
                "Door Height (inches)": info.get("Door Height (inches)", 48),
                "Bucket Type": info.get("Bucket Type", "Starter Bucket"),
                "Handle Type": info.get("Handle Type", "Rotary Handle"),
                "Cutouts": {
                    "RotoTract Cutout": info.get("Cutouts", {}).get("RotoTract Cutout", False),
                    "Fan Cutout": info.get("Cutouts", {}).get("Fan Cutout", True),
                    "Pemstud": info.get("Cutouts", {}).get("Pemstud", True),
                    "Device Panel Cutout": info.get("Cutouts", {}).get("Device Panel Cutout", True)
                },
                "Door Thickness (Ga)": info.get("Door Thickness (Ga)", 14)
            }
            
            st.subheader("🔧 Final Summary Dictionary")
            st.json(summary_dict)
            
            if st.button("Save Summary"):
                save_summary_json(summary_dict)
                st.success(f"Summary saved to: {os.path.join(json_folder, 'mcc_door_summary.json')}")
            
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    else:
        streamlit_chat()

if __name__ == "__main__":
    main()
