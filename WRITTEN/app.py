"""
HuggingFace Spaces entry point.
HF Spaces looks for app.py at the root — this just launches the Gradio UI.
"""
from ui.gradio_app import demo

if __name__ == "__main__":
    demo.launch()