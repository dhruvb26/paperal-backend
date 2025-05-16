import dspy
import os
from dotenv import load_dotenv
from typing import Dict, Any

load_dotenv()

# Configure DSPy with GPT-4
dspy.configure(lm=dspy.LM("openai/gpt-4", api_key=os.getenv("OPENAI_API_KEY")))

class StyleAnalyzer(dspy.Signature):
    """Analyze the writing style characteristics."""
    text = dspy.InputField(desc="Text to analyze for style characteristics")
    analysis = dspy.OutputField(desc="Focused analysis of key writing style characteristics")

class StyleAdapter(dspy.Signature):
    """Adapt text to match a user's writing style while maintaining similar length."""
    style_analysis = dspy.InputField(desc="Analysis of the target writing style")
    target_text = dspy.InputField(desc="Text to be adapted to match the style")
    output = dspy.OutputField(desc="Text rewritten in the analyzed style with similar length")

class EnhancedStyleAdapterProgram(dspy.Module):
    def __init__(self):
        super().__init__()
        self.analyzer = dspy.Predict(StyleAnalyzer)
        self.adapter = dspy.Predict(StyleAdapter)
    
    def forward(self, style_samples, target_text):
        # First, analyze the writing style
        style_analysis = self.analyzer(
            text=style_samples,
            prompt="""Analyze the writing style focusing on these key elements:
            1. Personal voice (first-person usage, experience sharing)
            2. Key phrases and expressions frequently used
            3. Technical terminology handling
            4. Sentence structure preferences
            Keep the analysis concise and focused on the most distinctive features."""
        )
        
        # Then adapt the text using the analysis
        adapted = self.adapter(
            style_analysis=style_analysis.analysis,
            target_text=target_text,
            prompt="""Rewrite the target text to match the analyzed style while:
            1. Keeping the length similar to the original text
            2. Maintaining all technical information
            3. Adding just enough personal voice to match the style
            4. Using at most one characteristic phrase
            5. Staying focused and concise
            
            IMPORTANT: The length of the adapted text should be similar to the original text."""
        )
        
        return {
            'style_analysis': style_analysis.analysis,
            'adapted_text': adapted.output
        }

def adapt_to_style(writing_samples: str, text_to_adapt: str) -> Dict[str, Any]:
    """
    Adapt a piece of text to match the writing style from provided samples.
    
    Args:
        writing_samples (str): Examples of the target writing style
        text_to_adapt (str): The text to be rewritten in the target style
        
    Returns:
        Dict containing:
            - style_analysis: Analysis of the writing style
            - adapted_text: The text rewritten in the target style
            
    Example:
        >>> samples = '''
        ... I've found that robust error handling is crucial in distributed systems.
        ... Through my testing, I've discovered that most issues stem from edge cases.
        ... '''
        >>> result = adapt_to_style(samples, "The function validates input parameters.")
        >>> print(result['adapted_text'])
    """
    program = EnhancedStyleAdapterProgram()
    return program(style_samples=writing_samples, target_text=text_to_adapt)

if __name__ == "__main__":
    # Example usage
    example_style = """
    I've found that robust error handling is crucial in distributed systems. Through my testing, 
    I've discovered that most issues stem from edge cases we didn't anticipate. When components fail, 
    having clear visibility into the error chain makes all the difference.

    One pattern I've had success with is implementing circuit breakers. They've helped prevent 
    cascading failures in our production systems, especially during high-load scenarios.
    """

    test_text = "The API endpoint validates user input and returns appropriate error messages."
    
    result = adapt_to_style(example_style, test_text)
    
    print("\nOriginal Text:")
    print("-" * 80)
    print(test_text)
    
    print("\nStyle Analysis:")
    print("-" * 80)
    print(result['style_analysis'])
    
    print("\nAdapted Text:")
    print("-" * 80)
    print(result['adapted_text'])