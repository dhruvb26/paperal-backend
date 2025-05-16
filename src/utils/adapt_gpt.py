import os
from typing import Dict, Any
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def adapt_text_style(writing_samples: str, text_to_adapt: str) -> Dict[str, Any]:
    """
    Adapt a piece of text to match the writing style from provided samples using OpenAI API.
    
    Args:
        writing_samples (str): Examples of the target writing style
        text_to_adapt (str): The text to be rewritten in the target style
        
    Returns:
        Dict containing:
            - adapted_text: The text rewritten in the target style
            - style_analysis: Analysis of the writing style
    """
    
    # System message with few-shot examples for better prompting
    system_message = {
        'role': 'system',
        'content': '''You are a writing style adaptation expert. Analyze the provided writing samples 
        and adapt the target text to match that style while maintaining the core meaning.
        
        Here are some examples of style adaptation:
        """
        Original: The data structure efficiently stores elements.
        Style: I love diving deep into technical details. In my experience, proper error handling is crucial.
        Adapted: From what I've found, this particular data structure does an excellent job at storing elements efficiently.
        """
        """
        Original: The function validates input parameters.
        Style: Through extensive testing, I've learned that edge cases matter most. Always verify your assumptions.
        Adapted: Based on my testing experience, I've implemented thorough input parameter validation in this function.
        """'''
    }

    # Create the messages for the chat completion
    messages = [
        system_message,
        {
            'role': 'user',
            'content': f'''Writing style examples:
            {writing_samples}
            
            Text to adapt:
            {text_to_adapt}
            
            First analyze the writing style, then adapt the text to match it while:
            1. Maintaining the same core meaning
            2. Keeping similar length
            3. Using similar tone and voice
            4. Preserving technical accuracy

            IMPORTANT: The length of the adapted text should be similar to the original text.
            
            Provide only the adapted text.'''
        }
    ]

    # Make the API call
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.5,
    )

    # Extract the response
    full_response = response.choices[0].message.content



    return {
        'adapted_text': full_response
    }

if __name__ == "__main__":
    # Example usage
    example_style = """
    I've found that robust error handling is crucial in distributed systems. Through my testing, 
    I've discovered that most issues stem from edge cases we didn't anticipate. When components fail, 
    having clear visibility into the error chain makes all the difference.
    """

    test_text = "I like to eat pizza"
    
    result = adapt_text_style(example_style, test_text)
    
    print("\nOriginal Text:")
    print("-" * 80)
    print(test_text)
    
    print("\nAdapted Text:")
    print("-" * 80)
    print(result['adapted_text'])
