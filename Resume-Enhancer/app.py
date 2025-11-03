import streamlit as st
import fitz  # PyMuPDF
import re
import os
from openai import OpenAI
from datetime import datetime
import json
from PIL import Image
import io
import base64
import cohere
import requests  # For Qwen API calls
from typing import Optional, Tuple

# --- Page Configuration ---
st.set_page_config(
    page_title="AI Resume Enhancer",
    page_icon="📄",
    layout="wide"
)

# --- Title and Description ---
st.title("📄 AI Resume Enhancer")
st.markdown("""
Transform your resume with AI-powered enhancements. Upload your resume, select sections to improve, 
and get professional, targeted enhancements for your desired role.
""")

# --- Sidebar for API Configuration ---
with st.sidebar:
    st.header("🔑 API Configuration")
    
    # OpenAI API Key (was Groq)
    openai_api_key = st.text_input("OpenAI API Key", type="password", key="openai_key")
    st.markdown("[Get an OpenAI API key](https://platform.openai.com/account/api-keys)")
    
    st.markdown("---")
    
    # Qwen Vision Model (Optional)
    st.subheader("🎨 Vision-Based OCR (Optional)")
    use_qwen_vision = st.checkbox("Use Qwen Vision Model for scanned PDFs?", value=False, 
                                   help="Enable for better OCR on scanned/image-heavy PDFs")
    
    if use_qwen_vision:
        qwen_api_key = st.text_input("Hugging Face Token (for Qwen)", type="password", key="qwen_key")
        st.markdown("[Get HF Token](https://huggingface.co/settings/tokens)")
        if qwen_api_key:
            st.success("✅ Qwen Vision Model configured!")
    else:
        qwen_api_key = None
        st.info("ℹ️ Using standard PyMuPDF extraction")
    
    st.markdown("---")
    
    if openai_api_key:
        st.success("✅ OpenAI API Key configured!")
    else:
        st.warning("⚠️ Please enter your OpenAI API key to proceed.")
    
    st.markdown("---")
    st.markdown("### 💡 Tips")
    st.markdown("""
    - Upload a PDF resume (standard or scanned)
    - Enable Qwen for scanned PDFs (OCR via Hugging Face)
    - Review extracted sections
    - Choose what to enhance
    - Get AI-powered improvements
    """)

# --- Initialize Session State ---
if 'resume_sections' not in st.session_state:
    st.session_state.resume_sections = {}
if 'enhanced_sections' not in st.session_state:
    st.session_state.enhanced_sections = {}
if 'full_text' not in st.session_state:
    st.session_state.full_text = ""

# --- Initialize OpenAI Client (replaces Groq) ---
openai_client = None
if openai_api_key:
    try:
        # Prefer setting environment variable for libraries that may use it
        os.environ["OPENAI_API_KEY"] = openai_api_key
        openai_client = OpenAI(api_key=openai_api_key)
    except Exception as e:
        st.error(f"Failed to initialize OpenAI client: {e}")


# --- Enhanced PDF Text Extraction Function ---
def extract_text_from_pdf(pdf_file, use_enhanced=True, openai_client=None):
    """
    Extract text from uploaded PDF file with enhanced extraction.
    Uses layout-aware text extraction and AI-powered structuring.
    """
    try:
        # Read the PDF file
        pdf_bytes = pdf_file.read()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        full_text = ""
        all_page_texts = []
        extraction_debug = {
            'pages': [],  # list of {'page': n, 'raw_text': str, 'blocks': [..]}
            'structured': None,
            'logs': []
        }
        
        # Progress bar for extraction
        progress_bar = st.progress(0.0)
        st.write(f"📖 Extracting text from {len(doc)} page(s)...")
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            # Method 1: Layout-aware text extraction with better handling
            page_text = ""
            page_blocks = []
            if use_enhanced:
                try:
                    # Get text with layout information (preserves columns, tables, etc.)
                    text_dict = page.get_text("dict")
                    
                    # Extract text blocks with better positioning
                    blocks = []
                    if isinstance(text_dict, dict) and "blocks" in text_dict:
                        for block in text_dict["blocks"]:
                            if isinstance(block, dict) and "lines" in block:
                                block_text = ""
                                for line in block["lines"]:
                                    if isinstance(line, dict) and "spans" in line:
                                        line_text = ""
                                        for span in line["spans"]:
                                            if isinstance(span, dict) and "text" in span:
                                                line_text += span["text"]
                                        block_text += line_text + "\n"
                                
                                if block_text.strip() and "bbox" in block:
                                    blocks.append({
                                        'text': block_text.strip(),
                                        'bbox': block['bbox']
                                    })
                        
                        # Sort blocks by vertical position (top to bottom)
                        blocks.sort(key=lambda b: (b['bbox'][1], b['bbox'][0]))
                        
                        # Combine blocks with proper spacing
                        for block in blocks:
                            if block['text']:
                                page_text += block['text'] + "\n\n"
                        page_blocks = blocks
                except:
                    pass  # Fall through to simple extraction
                
                # Fallback to simple extraction if enhanced fails
                if not page_text.strip():
                    page_text = str(page.get_text())
                    page_blocks = []
            else:
                # Simple extraction
                page_text = str(page.get_text())
            
            # Add page separator
            if page_text.strip():
                all_page_texts.append(f"--- Page {page_num + 1} ---\n{page_text}")
                full_text += page_text + "\n\n"
                extraction_debug['pages'].append({
                    'page': page_num + 1,
                    'raw_text': page_text,
                    'blocks': page_blocks
                })
            
            # Update progress
            progress_bar.progress((page_num + 1) / len(doc))
        
        doc.close()
        progress_bar.empty()
        
        # Use OpenAI to clean and structure the extracted text if available
        if use_enhanced and full_text.strip():
            with st.spinner("🤖 AI is structuring the extracted content..."):
                try:
                    # Prefer Cohere structure endpoint if configured
                    structured_text = None

                    if not structured_text and openai_client:
                        try:
                            structure_prompt = f"""You are an expert resume text normalizer specializing in PDF extraction cleanup.

**Input**: Raw, potentially malformed text extracted from a resume PDF
**Your Task**: Clean and normalize this text while preserving 100% of the original information

**Required Actions**:
1. Merge broken lines (e.g., "soft-\\nware" → "software")
2. Fix word breaks caused by column wrapping or hyphenation
3. Standardize section headers to Title Case (e.g., "WORK EXPERIENCE" → "Work Experience")
4. Preserve all: dates, numbers, company names, titles, achievements, contact info
5. Maintain chronological order within sections (don't reorder entries)
6. Add blank lines between distinct sections for clarity
7. Remove excessive whitespace while maintaining paragraph structure

**Critical Rules**:
- DO NOT add, invent, or remove any information
- DO NOT fix grammatical errors (preserve original wording)
- DO NOT reorder or reorganize sections
- If text is already well-structured, return it with minimal changes
- Preserve bullet point symbols (•, -, *, etc.) as-is

**Output Format**: Plain text with proper line breaks and spacing

**Example Transformation**:
Before: "WORK EXPER-\\nIENCE\\nSenior  Engineer  at\\nTech Corp  2020-2023\\n\\n\\nLed team"
After: "Work Experience\\nSenior Engineer at Tech Corp\\n2020-2023\\n\\nLed team"

**Raw Text**:
{full_text[:8000]}

**Cleaned Text**:"""
                            response = openai_client.chat.completions.create(
                                model="gpt-4o-mini-2024-07-18",
                                messages=[{"role":"user","content":structure_prompt}],
                                max_tokens=2048,
                                temperature=0.0  # Deterministic normalization - no creativity needed
                            )
                            structured_text = response.choices[0].message.content
                        except Exception as ge:
                            st.warning(f"OpenAI structuring failed: {ge}")

                    if structured_text and len(structured_text) > 100:
                        extraction_debug['structured'] = structured_text
                        full_text = structured_text
                        extraction_debug['logs'].append('Structured text produced by AI')
                        st.success("✨ AI successfully structured the resume content!")
                except Exception as e:
                    st.warning(f"AI structuring skipped: {e}. Using raw extraction.")

        # Optionally, produce JSON-structured sections via AI (cohere preferred)
        if use_enhanced and full_text.strip():
            try:
                struct_json = None

                if not struct_json and openai_client:
                    try:
                        parse_prompt = f"""You are a resume parsing expert. Given the cleaned resume text below, extract sections and return JSON list of objects with keys: name, content, start_char, end_char.

Text:
{full_text[:12000]}

Return ONLY valid JSON."""
                        gresp = openai_client.chat.completions.create(
                            model="gpt-4o-mini-2024-07-18",
                            messages=[{"role":"user","content":parse_prompt}],
                            max_tokens=2048,
                            temperature=0.0
                        )
                        text_out = gresp.choices[0].message.content
                        struct_json = extract_json_from_text(text_out)
                        if not struct_json:
                            extraction_debug['logs'].append('OpenAI JSON parse failed')
                    except Exception as ge:
                        extraction_debug['logs'].append(f"OpenAI JSON extraction failed: {ge}")
                if struct_json:
                    st.session_state.structured_sections = struct_json
                    extraction_debug['logs'].append('Structured JSON sections produced')
            except Exception as e:
                extraction_debug['logs'].append(f"Structured JSON extraction failed: {e}")
        
        # Attach debug to session state for UI inspection
        st.session_state.extraction_debug = extraction_debug

        return full_text.strip()

    except Exception as e:
        st.error(f"Error extracting text from PDF: {e}")
        return None


# --- Qwen Vision-Based Extraction (For Scanned PDFs) ---
def extract_text_with_qwen(pdf_file, hf_token: str) -> Optional[str]:
    """
    Extract text from PDF using Qwen Vision Model via Hugging Face Router API.
    Best for scanned PDFs or images with embedded text.
    
    Args:
        pdf_file: Uploaded PDF file object
        hf_token: Hugging Face API authentication token
    
    Returns:
        Extracted text or None if extraction fails
    """
    try:
        import time
        
        # Initialize Hugging Face Router API client (OpenAI-compatible)
        from openai import OpenAI
        
        client = OpenAI(
            api_key=hf_token,
            base_url="https://router.huggingface.co/v1"
        )
        
        # Read and convert PDF to images
        pdf_bytes = pdf_file.read()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        all_extracted_text = ""
        progress_bar = st.progress(0.0)
        
        st.write(f"🎨 Extracting text with Qwen Vision Model from {len(doc)} page(s)...")
        
        for page_num in range(min(len(doc), 10)):  # Limit to first 10 pages for cost
            try:
                # Convert PDF page to image
                pix = doc[page_num].get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better OCR
                img_data = pix.tobytes("png")
                
                # Encode image to base64
                import base64
                img_base64 = base64.b64encode(img_data).decode('utf-8')
                
                # Call Qwen Vision Model via Hugging Face Router
                response = client.chat.completions.create(
                    model="Qwen/Qwen3-VL-8B-Instruct:novita",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Extract all text from this resume image. Preserve formatting and structure as much as possible. Return only the extracted text, nothing else."
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {"url": f"data:image/png;base64,{img_base64}"}
                                }
                            ]
                        }
                    ],
                    stream=False,
                    max_tokens=2048
                )
                
                if response and response.choices and response.choices[0].message.content:
                    extracted = response.choices[0].message.content
                    all_extracted_text += extracted + "\n\n---PAGE BREAK---\n\n"
                
                # Update progress
                progress_bar.progress((page_num + 1) / min(len(doc), 10))
                
                # Add small delay to respect API rate limits
                time.sleep(0.5)
                
            except Exception as page_error:
                st.warning(f"⚠️ Failed to extract page {page_num + 1}: {page_error}")
                continue
        
        st.success("✅ Qwen extraction completed!")
        return all_extracted_text.strip() if all_extracted_text else None
        
    except ImportError:
        st.error("❌ OpenAI client not installed. Install with: pip install openai")
        return None
    except Exception as e:
        st.error(f"❌ Qwen extraction error: {e}")
        return None


# --- Resume Section Parser ---
def parse_resume_sections(text, use_ai=False, openai_client=None):
    """
    Parse resume text into logical sections using pattern matching and optionally AI.
    Common sections: Contact, Summary, Experience, Education, Skills, Projects, Certifications
    """
    sections = {}
    
    # Clean and normalize text
    text = text.strip()
    
    # If AI-powered parsing is available, use it for better section detection
    if use_ai and openai_client and len(text) > 100:
        try:
            with st.spinner("🤖 AI is identifying resume sections..."):
                parse_prompt = f"""You are an expert resume section extractor with perfect JSON output capabilities.

**Task**: Parse the resume text below and extract all distinct sections with their content.

**Standard Resume Sections** (use these names when you identify them):
- Contact Information
- Professional Summary
- Work Experience
- Education
- Skills
- Projects
- Certifications
- Awards
- Publications
- Languages

**Instructions**:
1. Identify section boundaries in the resume
2. Extract the full content for each section
3. Normalize section names to match standard names above where applicable
4. Preserve all content exactly as written
5. If a section doesn't match standard names, use the exact header from the resume

**Output Format**: Return ONLY valid JSON array, no markdown, no explanations:

[
  {{
    "section_name": "Professional Summary",
    "content": "Experienced software engineer with 8 years..."
  }},
  {{
    "section_name": "Work Experience",
    "content": "Senior Engineer at Company X\\n2020-2023\\n- Led team of 5..."
  }}
]

**Edge Cases**:
- If no clear sections: Return [{{"section_name": "Full Resume", "content": "..."}}]
- If section header is unclear: Use the closest standard name
- If multiple similar sections (e.g., "Education" and "Academic Background"): Merge into one

**Resume Text**:
{text[:10000]}

**JSON Output**:"""

                response = openai_client.chat.completions.create(
                    model="gpt-4o-mini-2024-07-18",
                    messages=[{"role":"user","content":parse_prompt}],
                    max_tokens=2000,
                    temperature=0.0  # Deterministic for consistent section extraction
                )
                ai_response = response.choices[0].message.content

                # Parse JSON response
                ai_sections = {}
                try:
                    # Use the extract_json_from_text helper to handle markdown wrapping
                    sections_list = extract_json_from_text(ai_response)

                    if sections_list and isinstance(sections_list, list):
                        # Convert list of section objects to dictionary
                        for section_obj in sections_list:
                            if isinstance(section_obj, dict) and 'section_name' in section_obj and 'content' in section_obj:
                                ai_sections[section_obj['section_name']] = section_obj['content']

                        # If AI found sections, use them
                        if len(ai_sections) >= 1:
                            st.success(f"✨ AI identified {len(ai_sections)} sections!")
                            return ai_sections
                    else:
                        st.warning("AI response was not in expected JSON format. Using pattern matching...")

                except Exception as parse_error:
                    st.warning(f"Failed to parse AI JSON response: {parse_error}. Using pattern matching...")
        except Exception as e:
            st.warning(f"AI section detection failed: {e}. Using pattern matching...")
    
    # Fallback to pattern-based section detection
    # Define common section headers (case-insensitive patterns)
    section_patterns = {
        'Contact Information': r'(?i)^(contact\s*information|personal\s*details|contact\s*details)',
        'Summary': r'(?i)^(professional\s*summary|summary|profile|objective|about\s*me)',
        'Experience': r'(?i)^(work\s*experience|professional\s*experience|experience|employment\s*history)',
        'Education': r'(?i)^(education|academic\s*background|qualifications)',
        'Skills': r'(?i)^(skills|technical\s*skills|core\s*competencies|expertise)',
        'Projects': r'(?i)^(projects|key\s*projects|notable\s*projects)',
        'Certifications': r'(?i)^(certifications|certificates|licenses)',
        'Awards': r'(?i)^(awards|honors|achievements)',
        'Publications': r'(?i)^(publications|papers|research)',
        'Languages': r'(?i)^(languages|language\s*proficiency)',
    }
    
    # Find all section headers and their positions
    section_matches = []
    for section_name, pattern in section_patterns.items():
        for match in re.finditer(pattern, text, re.MULTILINE):
            section_matches.append({
                'name': section_name,
                'start': match.start(),
                'end': match.end()
            })
    
    # Sort by position in document
    section_matches.sort(key=lambda x: x['start'])
    
    # Extract content for each section
    for i, section in enumerate(section_matches):
        start_pos = section['end']
        # End position is the start of next section or end of document
        end_pos = section_matches[i + 1]['start'] if i + 1 < len(section_matches) else len(text)
        
        content = text[start_pos:end_pos].strip()
        
        # Only add if content is substantial
        if content and len(content) > 10:
            sections[section['name']] = content
    
    # If no sections found, try to extract top portion as contact/summary
    if not sections:
        # Take first 1000 characters as preliminary section
        sections['Full Resume'] = text[:1000] + "..." if len(text) > 1000 else text
        if len(text) > 1000:
            sections['Remaining Content'] = text[1000:]
    
    return sections


# --- JSON Extraction Helper ---
def extract_json_from_text(text):
    """
    Safely extract JSON from LLM response (which may be wrapped in markdown code blocks).
    Returns parsed JSON object or None if extraction fails.
    """
    try:
        # Try direct parse first
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Try to extract from markdown code blocks
    try:
        if '```json' in text:
            start = text.find('```json') + 7
            end = text.find('```', start)
            if end > start:
                json_str = text[start:end].strip()
                return json.loads(json_str)
        elif '```' in text:
            start = text.find('```') + 3
            end = text.find('```', start)
            if end > start:
                json_str = text[start:end].strip()
                return json.loads(json_str)
    except Exception:
        pass
    
    # Try to find first { and last }
    try:
        start_idx = text.find('{')
        end_idx = text.rfind('}')
        if start_idx >= 0 and end_idx > start_idx:
            json_str = text[start_idx:end_idx + 1]
            return json.loads(json_str)
    except Exception:
        pass
    
    return None


# --- AI Enhancement Function ---
def enhance_section(section_name, section_content, enhancement_request, openai_client):
    """
    Use AI to enhance a specific resume section based on user request.
    """
    if not openai_client:
        return "Error: OpenAI client not initialized. Please provide API key."
    
    try:
        prompt = f"""You are a senior resume writer and ATS optimization specialist with 15+ years of experience helping candidates land roles at Fortune 500 companies and top tech firms.

**Your Task**: Transform the resume section below according to the specific enhancement request, balancing impact with authenticity.

**Section Being Enhanced**: {section_name}

**Current Content**:
{section_content}

**User's Enhancement Request**: {enhancement_request}

**Enhancement Guidelines** (Priority Order):
1. **Preserve Authenticity**: NEVER invent facts, credentials, dates, or achievements not present in the original
2. **Quantify Impact**: Where metrics are implied but not stated, make them explicit (e.g., "managed team" → "managed team of 5 engineers")
3. **Action-Oriented Language**: Start bullets with strong verbs (Architected, Spearheaded, Optimized, Delivered, Transformed, Led, Built)
4. **ATS Optimization**: Use industry keywords from target role; avoid tables, images, columns, or unusual characters
5. **Conciseness**: Target 3-5 bullets per role; 15-25 words per bullet for maximum impact
6. **Professional Tone**: Executive-level, confident but not arrogant, achievement-focused
7. **Role Relevance**: Emphasize experiences matching the target role; deprioritize irrelevant details

**Quality Checks** (Apply to every bullet):
- Structure: Action Verb + Task/Project + Quantifiable Result/Impact
- Avoid: Generic phrases ("responsible for", "duties included", "helped with")
- Ensure: Technical terms spelled correctly, dates formatted consistently
- No: Superlatives without proof ("world's best", "perfect", "flawless")

**Example Transformation**:
Before: "Responsible for managing software development projects and working with team members."
After: "Led cross-functional team of 8 engineers to deliver 3 enterprise applications, reducing deployment time by 40%"

**Output Instructions**:
- Provide ONLY the enhanced content, no preamble or explanations
- Maintain the original structure (bullets, paragraphs, etc.)
- If enhancement request is unclear or inappropriate, apply general best practices
- Keep the same number of bullet points or add 1-2 if content justifies it

**Enhanced Section**:"""

        response = openai_client.chat.completions.create(
            model="gpt-4o-mini-2024-07-18",
            messages=[{"role":"user","content":prompt}],
            max_tokens=1000,
            temperature=0.7  # Creative enhancement while maintaining professionalism
        )
        enhanced_content = response.choices[0].message.content
        
        return enhanced_content.strip()
    
    except Exception as e:
        return f"Error during enhancement: {str(e)}"


# --- Main Application Layout ---
st.markdown("---")

# File Upload Section
st.header("📤 Step 1: Upload Your Resume")
uploaded_file = st.file_uploader(
    "Upload your resume (PDF format)",
    type=['pdf'],
    help="Upload a PDF version of your resume for analysis and enhancement"
)

if uploaded_file:
    # Determine which extraction method to use
    extraction_method = "PyMuPDF (Fast)"
    extracted_text = None
    
    # Reset file pointer for potential re-reads
    uploaded_file.seek(0)
    
    # Try primary extraction method (PyMuPDF - always fastest)
    with st.spinner("📖 Extracting text from your resume..."):
        extracted_text = extract_text_from_pdf(uploaded_file, openai_client=openai_client)
    
    # If Qwen is enabled and PyMuPDF extracted minimal text, try Qwen
    if use_qwen_vision and qwen_api_key:
        text_length = len(extracted_text) if extracted_text else 0
        
        if text_length < 500:  # Minimal text threshold (likely a scanned PDF)
            st.info("📝 Detected scanned PDF. Attempting Qwen Vision extraction...")
            
            uploaded_file.seek(0)
            qwen_text = extract_text_with_qwen(uploaded_file, qwen_api_key)
            
            if qwen_text and len(qwen_text) > text_length:
                extracted_text = qwen_text
                extraction_method = "Qwen Vision Model (OCR)"
                st.success("✅ Using Qwen Vision extraction for better results!")
            else:
                extraction_method = "PyMuPDF (Fast)"
    
    if extracted_text:
        st.session_state.full_text = extracted_text
        
        # Show extraction method used
        st.info(f"📌 Extraction method: **{extraction_method}**")
        
        # Parse sections
        with st.spinner("🔍 Analyzing resume structure..."):
            sections = parse_resume_sections(extracted_text, use_ai=True, openai_client=openai_client)
            st.session_state.resume_sections = sections
        
        st.success(f"✅ Successfully extracted {len(sections)} sections from your resume!")
        
        # ============================================================
        # PHASE 1: EXTRACTED SECTIONS (READ-ONLY)
        # ============================================================
        st.markdown("---")
        st.header("📋 Phase 1: Extracted Sections from Your Resume")
        st.markdown("Review the sections automatically detected from your resume PDF:")
        
        if sections:
            # Create tabs for each extracted section
            tab_names = list(sections.keys())
            tabs = st.tabs(tab_names)
            
            for idx, (section_name, section_content) in enumerate(sections.items()):
                with tabs[idx]:
                    st.subheader(f"📌 {section_name}")
                    st.text_area(
                        f"{section_name} content",
                        value=section_content,
                        height=300,
                        key=f"extracted_{section_name}",
                        disabled=True
                    )
        
        # ============================================================
        # PHASE 2: ENHANCEMENT SECTION
        # ============================================================
        st.markdown("---")
        st.header("✨ Phase 2: Enhance Your Sections")
        st.markdown("Select sections to enhance and provide specific improvement requests:")
        
        if sections:
            # Section selection
            col1, col2 = st.columns([2, 1])
            
            with col1:
                selected_section = st.selectbox(
                    "Select a section to enhance:",
                    options=list(sections.keys()),
                    key="section_selector"
                )
            
            with col2:
                st.markdown("**Enhancement Request**")
            
            if selected_section:
                section_content = sections[selected_section]
                
                # Enhancement input
                enhancement_request = st.text_area(
                    "What would you like to improve about this section?",
                    placeholder=f"Example: 'Tailor for Senior AI Engineer role' or 'Highlight leadership achievements with metrics'",
                    height=100,
                    key=f"enhancement_request_{selected_section}"
                )
                
                # Enhancement button
                col_btn1, col_btn2, col_btn3 = st.columns([2, 2, 1])
                
                with col_btn1:
                    enhance_button = st.button(
                        "✨ Enhance Section",
                            disabled=not openai_api_key or not enhancement_request,
                        use_container_width=True,
                        key=f"enhance_btn_{selected_section}"
                    )
                
                # Process enhancement
                if enhance_button and enhancement_request:
                    with st.spinner(f"🤖 Enhancing '{selected_section}'..."):
                        enhanced = enhance_section(
                            selected_section,
                            section_content,
                            enhancement_request,
                            openai_client
                        )
                        st.session_state.enhanced_sections[selected_section] = enhanced
                        st.rerun()
        
        # Display enhanced sections (if any)
        if st.session_state.enhanced_sections:
            st.markdown("---")
            st.header("🎯 Enhanced Sections")
            st.markdown("Below are your enhanced sections. Review and edit as needed:")
            
            enhanced_tab_names = list(st.session_state.enhanced_sections.keys())
            enhanced_tabs = st.tabs(enhanced_tab_names)
            
            for idx, (section_name, enhanced_text) in enumerate(st.session_state.enhanced_sections.items()):
                with enhanced_tabs[idx]:
                    st.subheader(f"✅ {section_name} (Enhanced)")
                    
                    # Editable enhanced content
                    edited_text = st.text_area(
                        f"Enhanced {section_name} (editable)",
                        value=enhanced_text,
                        height=300,
                        key=f"edited_enhanced_{section_name}"
                    )
                    
                    # Update if user edits
                    st.session_state.enhanced_sections[section_name] = edited_text
                    
                    # Comparison view
                    with st.expander("📊 View Original vs Enhanced"):
                        col_orig, col_enh = st.columns(2)
                        
                        with col_orig:
                            st.markdown("**Original**")
                            st.text_area(
                                f"Original {section_name}",
                                value=sections.get(section_name, ""),
                                height=250,
                                disabled=True,
                                key=f"compare_orig_{section_name}"
                            )
                        
                        with col_enh:
                            st.markdown("**Enhanced**")
                            st.text_area(
                                f"Enhanced {section_name}",
                                value=edited_text,
                                height=250,
                                disabled=True,
                                key=f"compare_enh_{section_name}"
                            )
                    
                    # Allow removing enhanced sections
                    if st.button("❌ Remove this enhanced section", key=f"remove_{section_name}"):
                        del st.session_state.enhanced_sections[section_name]
                        st.rerun()
        
        # ============================================================
        # EXPORT SECTION (Only shown if enhancements exist)
        # ============================================================
        if st.session_state.enhanced_sections:
            st.markdown("---")
            st.header("💾 Phase 3: Export Your Enhanced Resume")
            st.markdown("Download your enhanced resume in your preferred format:")
            
            # Build complete enhanced resume
            enhanced_resume_text = ""
            for section_name in sections.keys():
                enhanced_resume_text += f"\n{'='*60}\n"
                enhanced_resume_text += f"{section_name.upper()}\n"
                enhanced_resume_text += f"{'='*60}\n\n"
                
                if section_name in st.session_state.enhanced_sections:
                    enhanced_resume_text += st.session_state.enhanced_sections[section_name]
                else:
                    enhanced_resume_text += sections[section_name]
                
                enhanced_resume_text += "\n\n"
            
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                st.download_button(
                    label="📥 Download Enhanced Resume (TXT)",
                    data=enhanced_resume_text,
                    file_name=f"enhanced_resume_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                    mime="text/plain",
                    use_container_width=True
                )
            
            with col2:
                # JSON export with metadata
                export_data = {
                    'original_sections': sections,
                    'enhanced_sections': st.session_state.enhanced_sections,
                    'timestamp': datetime.now().isoformat()
                }
                st.download_button(
                    label="📥 Download as JSON",
                    data=json.dumps(export_data, indent=2),
                    file_name=f"resume_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    use_container_width=True
                )
            
            with col3:
                if st.button("🔄 Start Over", use_container_width=True):
                    st.session_state.enhanced_sections = {}
                    st.session_state.resume_sections = {}
                    st.rerun()
            
            st.info("💡 **Tip**: Download and paste into your preferred resume editor or ATS system.")

else:
    # Instructions when no file uploaded
    st.info("👆 Upload your resume PDF to get started!")
    
    with st.expander("📖 How to Use This Tool"):
        st.markdown("""
        ### Step-by-Step Guide
        
        1. **Upload Resume**: Click the upload button and select your resume PDF
        2. **Review Sections**: The app automatically detects and organizes your resume sections
        3. **Request Enhancements**: For each section, specify how you'd like it improved:
           - "Enhance for Data Scientist position"
           - "Add more quantifiable achievements"
           - "Make skills match AI Engineer requirements"
           - "Improve project descriptions with technical details"
        4. **Review & Edit**: Review AI suggestions and edit as needed
        5. **Export**: Download your enhanced resume in your preferred format
        
        ### Best Practices
        
        - ✅ Be specific with enhancement requests
        - ✅ Review and customize AI suggestions
        - ✅ Maintain honesty - don't embellish credentials
        - ✅ Tailor different sections for different roles
        - ✅ Use the comparison view to ensure improvements
        
        ### Example Enhancement Requests
        
        - "Enhance this experience section for a Senior AI Engineer role at a tech company"
        - "Rewrite these project descriptions to highlight machine learning expertise"
        - "Optimize skills section for ATS systems in data science roles"
        - "Make the summary more compelling and achievement-focused"
        """)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center'>
    <p>Built with ❤️ using Streamlit and OpenAI | <strong>AI Resume Enhancer</strong></p>
    <p style='font-size: 0.8em; color: #666;'>Enhance your career prospects with AI-powered resume optimization</p>
</div>
""", unsafe_allow_html=True)
