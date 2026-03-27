from pathlib import Path

from auto_validator.config import settings
from auto_validator.exceptions import IntegrationError
from auto_validator.integrations.base import BaseIntegration, console


class DalleIntegration(BaseIntegration):
    def generate_image(self, prompt: str, project_id: str, filename: str = "image") -> str:
        """
        Generate an image from a prompt.
        Returns URL (live) or placeholder path (dry-run / disabled).
        """
        if not settings.dalle_enabled:
            return f"[DALL-E DISABLED] prompt: {prompt[:60]}..."

        if self.dry_run:
            self._log_dry_run("DALL-E.generate_image", {"prompt": prompt[:200], "project_id": project_id})
            return f"[DRY RUN] https://dalle.placeholder/{project_id}/{filename}.png"

        if not settings.openai_api_key:
            raise IntegrationError("OPENAI_API_KEY not configured for DALL-E.")

        try:
            from openai import OpenAI
            import httpx

            client = OpenAI(api_key=settings.openai_api_key)
            response = client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1024",
                quality="standard",
                n=1,
            )
            image_url = response.data[0].url

            # Download and save locally
            save_dir = settings.output_dir / "images" / project_id
            save_dir.mkdir(parents=True, exist_ok=True)
            save_path = save_dir / f"{filename}.png"

            with httpx.Client() as http_client:
                img_response = http_client.get(image_url)
                img_response.raise_for_status()
                save_path.write_bytes(img_response.content)

            console.print(f"[green]Image saved:[/green] {save_path}")
            return str(save_path)

        except Exception as exc:
            raise IntegrationError(f"DALL-E error: {exc}") from exc
