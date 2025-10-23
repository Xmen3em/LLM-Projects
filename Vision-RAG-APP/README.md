# Vision RAG with Cohere Embed-4 🖼️

A powerful Retrieval-Augmented Generation (RAG) application that combines visual document search with intelligent text generation. This app uses Cohere's Embed-4 multimodal embedding model for image search and Groq's GPT-OSS-120B for generating contextual answers.

## 🌟 Features

- **Multimodal Document Search**: Upload images and PDFs to create a searchable knowledge base
- **Intelligent Image Retrieval**: Uses Cohere Embed-4 to find the most relevant images based on your questions
- **AI-Powered Answers**: Generates detailed responses using Groq's GPT-OSS-120B model
- **PDF Processing**: Automatically extracts pages from PDFs as images for embedding
- **Sample Dataset**: Pre-loaded with financial data images from major companies (Tesla, Netflix, Nike, Google, Accenture, Tencent)
- **Interactive UI**: Clean, user-friendly Streamlit interface

## 🚀 How It Works

1. **Document Embedding**: Images and PDF pages are converted to high-dimensional embeddings using Cohere's Embed-4 model
2. **Query Processing**: Your questions are embedded using the same model
3. **Similarity Search**: The system finds the most relevant image based on cosine similarity
4. **Answer Generation**: Groq's GPT-OSS-120B generates contextual answers based on the retrieved image and question

## 🛠️ Installation

### Prerequisites

- Python 3.8 or higher
- API keys for:
  - [Cohere](https://dashboard.cohere.com/api-keys)
  - [Groq](https://console.groq.com/keys)

### Setup

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd Vision-RAG-APP
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```bash
   streamlit run app.py
   ```

4. **Access the app:**
   Open your browser and go to `http://localhost:8501`

## 📋 Dependencies

- `cohere>=5.0.0` - For multimodal embeddings
- `langchain-groq>=0.1.0` - For Groq integration
- `streamlit>=1.28.0` - Web interface
- `Pillow>=10.0.0` - Image processing
- `PyMuPDF>=1.23.0` - PDF processing
- `numpy>=1.24.0` - Numerical operations
- `requests>=2.31.0` - HTTP requests
- `tqdm>=4.66.0` - Progress bars

## 🔑 API Configuration

### Getting API Keys

1. **Cohere API Key:**
   - Visit [Cohere Dashboard](https://dashboard.cohere.com/api-keys)
   - Sign up/login and create a new API key
   - Required for image embedding functionality

2. **Groq API Key:**
   - Visit [Groq Console](https://console.groq.com/keys)
   - Sign up/login and generate an API key
   - Required for answer generation

### Setting Up Keys

Enter your API keys in the sidebar when you run the application. The keys are stored securely in your session and are not saved permanently.

## 📖 Usage Guide

### 1. Load Sample Images
- Click "Load Sample Images" to download pre-configured financial data images
- These include charts and data from major companies

### 2. Upload Your Own Content
- Use the file uploader to add your own images (PNG, JPG, JPEG)
- Upload PDF documents - they'll be automatically converted to page images
- Supported formats: PNG, JPG, JPEG, PDF

### 3. Ask Questions
- Type your question in the text input field
- Examples:
  - "What is Tesla's revenue?"
  - "Show me Nike's profit margins"
  - "What are Google's key financial metrics?"

### 4. Get Intelligent Answers
- The system will find the most relevant image
- Display the retrieved image with context
- Generate a detailed answer using AI

## 🏗️ Architecture

### Core Components

1. **Image Processing Pipeline**
   - Image resizing and optimization
   - Base64 encoding for API compatibility
   - PDF page extraction using PyMuPDF

2. **Embedding System**
   - Cohere Embed-4 for multimodal embeddings
   - Efficient similarity search using numpy
   - Caching for improved performance

3. **Answer Generation**
   - Context-aware prompting
   - Groq GPT-OSS-120B for high-quality responses
   - Filename-based context hints for better accuracy

### Technical Details

- **Max Image Resolution**: 1568x1568 pixels (automatically resized)
- **Embedding Dimension**: Determined by Cohere Embed-4 model
- **Search Algorithm**: Cosine similarity with numpy dot product
- **Caching**: Streamlit caching for embeddings (1 hour TTL)

## 🎯 Use Cases

- **Financial Analysis**: Analyze charts, graphs, and financial documents
- **Document Q&A**: Ask questions about visual content in reports
- **Data Visualization**: Extract insights from charts and infographics
- **Research**: Search through visual research materials
- **Education**: Interactive learning with visual content

## ⚠️ Limitations

- **Vision Model**: Groq doesn't support direct image analysis, so the system uses filename-based context inference
- **File Size**: Large PDFs may take time to process
- **API Limits**: Subject to Cohere and Groq API rate limits
- **Language**: Currently optimized for English content

## 🔧 Customization

### Adding New Sample Images

Modify the `images` dictionary in the `download_and_embed_sample_images()` function:

```python
images = {
    "your_image.png": "https://your-image-url.com/image.png",
    # Add more images here
}
```

### Changing Models

- **Embedding Model**: Update the model name in `compute_image_embedding()` function
- **LLM Model**: Change the model parameter in the `ChatGroq` initialization

### UI Customization

- Modify Streamlit components in the main application code
- Update the page configuration, title, or layout as needed

## 🐛 Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are installed correctly
2. **API Key Issues**: Verify your API keys are valid and have sufficient credits
3. **Memory Issues**: Large PDFs might cause memory problems - try smaller files
4. **Slow Performance**: First-time embedding generation takes time - subsequent queries are cached

### Error Messages

- **"Prerequisites not met"**: Check API keys and file paths
- **"Embedding failed"**: Verify Cohere API key and internet connection
- **"Answer generation failed"**: Check Groq API key and model availability


## 🤝 Contributing

Feel free to submit issues, feature requests, or pull requests to improve the application.
