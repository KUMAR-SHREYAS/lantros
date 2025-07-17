import os
from dotenv import load_dotenv
import google.generativeai as genai
from groq import Groq, RateLimitError, APIStatusError

# Load environment variables from .env in the project root
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env'))

# Set your API keys as environment variables or directly here
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Log whether API keys are loaded (do not print the actual keys)
print(f"[llm_utils] GROQ_API_KEY loaded: {'YES' if GROQ_API_KEY else 'NO'}")
print(f"[llm_utils] GEMINI_API_KEY loaded: {'YES' if GEMINI_API_KEY else 'NO'}")

# .env file in projstillect root should contain:
# GROQ_API_KEY=your_groq_api_key
# GEMINI_API_KEY=your_gemini_api_key

groq_models = [
    "llama3-70b-8192",  # Llama 3 70B
    "llama3-8b-8192",   # Llama 3 8B
    "mixtral-8x7b-32768", # Mixtral 8x7B
    "gemma-7b-it",      # Gemma 7B
]

gemini_models = [
    "gemini-2.5-pro",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite-preview-06-17",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
    "gemini-1.5-pro",
]

def call_groq(messages, model_list=None):
    if model_list is None:
        model_list = groq_models
    client = Groq(api_key=GROQ_API_KEY)
    last_error = None
    for model in model_list:
        try:
            chat_completion = client.chat.completions.create(
                messages=messages,
                model=model,
            )
            return chat_completion.choices[0].message.content
        except RateLimitError as e:
            last_error = e
            continue  # Try next model
        except APIStatusError as e:
            if getattr(e, 'status_code', None) == 429:
                last_error = e
                continue
            else:
                raise
        except Exception as e:
            last_error = e
            continue
    raise RuntimeError(f"All Groq models failed. Last error: {last_error}")

def call_gemini(prompt, model_list=None):
    if model_list is None:
        model_list = gemini_models
    genai.configure(api_key=GEMINI_API_KEY)
    last_error = None
    for model in model_list:
        try:
            model_obj = genai.GenerativeModel(model)
            response = model_obj.generate_content(prompt)
            return response.text
        except Exception as e:
            # If 404 error, print available models for debugging
            if hasattr(e, 'args') and any('404' in str(arg) for arg in e.args):
                print(f"404 error for model '{model}'. Listing available Gemini models:")
                print(get_available_gemini_models())
            last_error = e
            continue
    raise RuntimeError(f"All Gemini models failed. Last error: {last_error}")

def personalize_with_llm(llm, user_query, retrieved_content, model="", messages=None, prompt_override=None):
    """
    llm: 'groq' or 'gemini'
    user_query: str
    retrieved_content: str
    model: model name for groq/gemini (optional, if you want to force a specific model)
    messages: list of chat messages (for Groq)
    prompt_override: str, full prompt (for Gemini)
    """
    if llm == "groq":
        if messages is not None:
            if model:
                return call_groq(messages, [model])
            else:
                return call_groq(messages)
        else:
            messages = [
                {"role": "system", "content": "You are a helpful assistant. Use the following context to answer the user's question."},
                {"role": "user", "content": f"Context: {retrieved_content}\n\nQuestion: {user_query}"}
            ]
            if model:
                return call_groq(messages, [model])
            else:
                return call_groq(messages)
    elif llm == "gemini":
        if prompt_override is not None:
            if model:
                return call_gemini(prompt_override, [model])
            else:
                return call_gemini(prompt_override)
        else:
            prompt = f"Context: {retrieved_content}\n\nQuestion: {user_query}\n\nAnswer as helpfully as possible."
            if model:
                return call_gemini(prompt, [model])
            else:
                return call_gemini(prompt)
    else:
        return "Invalid LLM selection."

def list_groq_models():
    """Return the list of configured Groq models."""
    return groq_models

def list_gemini_models():
    """Return the list of available Gemini models (those that support generateContent), with 'models/' or 'model/' prefix removed."""
    genai.configure(api_key=GEMINI_API_KEY)
    try:
        return [m.name.replace('models/', '').replace('model/', '') for m in genai.list_models() if 'generateContent' in getattr(m, 'supported_generation_methods', [])]
    except Exception:
        return [name.replace('models/', '').replace('model/', '') for name in gemini_models] 