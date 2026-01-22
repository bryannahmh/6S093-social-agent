import os
import replicate
from replicate.exceptions import ReplicateError


class ImageGenerator:
    """Generates images using fine-tuned Replicate Flux model."""
    
    def __init__(
        self,
        replicate_username: str = "sundai-club",
        model_name: str = "bry_model",
        trigger_word: str = "TOK",
    ):
        """
        Initialize the image generator.
        
        Args:
            replicate_username: Your Replicate username
            model_name: Name of your fine-tuned model
            trigger_word: Trigger word used during fine-tuning (e.g., "TOK")
        """
        self.replicate_username = replicate_username
        self.model_name = model_name
        self.trigger_word = trigger_word
        self.model_path = f"{replicate_username}/{model_name}"
        
        # Replicate will use REPLICATE_API_TOKEN from environment if set
        # Make sure to set it in your .env file
    
    def get_latest_version(self):
        """Get the latest version of the fine-tuned model."""
        try:
            model = replicate.models.get(self.model_path)
            versions = model.versions.list()
            if versions:
                return versions[0]
            else:
                raise ValueError(f"No versions found for model {self.model_path}")
        except ReplicateError as e:
            raise ValueError(f"Error accessing model {self.model_path}: {e}")
    
    def generate_image(
        self,
        prompt: str,
        guidance_scale: float = 7.5,
        model_type: str = "dev",
        num_inference_steps: int = None,
    ) -> str:
        """
        Generate an image using the fine-tuned model.
        
        Args:
            prompt: Text prompt for image generation. Include the trigger word
                   (e.g., "TOK") to activate the fine-tuned style.
            guidance_scale: How much attention the model pays to the prompt (1-50)
            model_type: "dev" for full quality, "schnell" for faster generation
            num_inference_steps: Number of inference steps (required for "schnell")
        
        Returns:
            URL of the generated image
        """
        latest_version = self.get_latest_version()
        
        # Prepare input parameters
        input_params = {
            "prompt": prompt,
            "guidance_scale": guidance_scale,
            "model": model_type,
        }
        
        # Add inference steps for schnell model
        if model_type == "schnell" and num_inference_steps is None:
            num_inference_steps = 4
        if num_inference_steps is not None:
            input_params["num_inference_steps"] = num_inference_steps
        
        try:
            output = replicate.run(latest_version, input=input_params)
            generated_img_url = str(output[0])
            return generated_img_url
        except Exception as e:
            raise RuntimeError(f"Error generating image: {e}")
    
    def generate_bouquet_image(
        self,
        description: str,
        letter: str = None,
        guidance_scale: float = 7.5,
    ) -> str:
        """
        Generate an image of a bouquet with optional letter.
        
        Args:
            description: Description of the bouquet (e.g., "extravagant rose bouquets")
            letter: Optional letter to include on the bouquet (e.g., "B")
            guidance_scale: Guidance scale for generation
        
        Returns:
            URL of the generated image
        """
        # Build prompt with trigger word
        prompt_parts = [
            f"A photo of Mexican-style {description}",
            "also known as ramos buchones in Spanish",
        ]
        
        if letter:
            prompt_parts.append(f"with the letter {letter} on it")
        
        prompt = ", ".join(prompt_parts) + "."
        
        # Ensure trigger word is included for fine-tuning activation
        if self.trigger_word not in prompt:
            prompt = f"{self.trigger_word} {prompt}"
        
        return self.generate_image(prompt, guidance_scale=guidance_scale)


def generate_image_for_post(post_text: str, brand_docs: str = None) -> str:
    """
    Generate an image based on post text and brand context.
    
    Args:
        post_text: The generated post text
        brand_docs: Optional brand documents for context
    
    Returns:
        URL of the generated image
    """
    generator = ImageGenerator()
    
    # Extract relevant keywords from post for image generation
    # You can enhance this with LLM to generate better image prompts
    prompt = f"{generator.trigger_word} A photo of Mexican-style extravagant rose bouquets, also known as ramos buchones in Spanish"
    
    return generator.generate_image(prompt)
