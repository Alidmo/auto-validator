from auto_validator.config import settings
from auto_validator.exceptions import IntegrationError
from auto_validator.integrations.base import BaseIntegration, console


class GoogleDocsIntegration(BaseIntegration):
    def create_doc(self, title: str, content: str) -> str:
        """Create a Google Doc and return the shareable URL."""
        if self.dry_run:
            self._log_dry_run("GoogleDocs.create_doc", {"title": title, "content_length": len(content)})
            console.print(f"[dim]--- Google Doc content preview ---[/dim]")
            console.print(content[:800] + ("..." if len(content) > 800 else ""))
            return f"[DRY RUN] https://docs.google.com/document/d/mock-{title[:20].replace(' ', '-')}"

        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build

            creds = service_account.Credentials.from_service_account_file(
                settings.google_credentials_path,
                scopes=[
                    "https://www.googleapis.com/auth/documents",
                    "https://www.googleapis.com/auth/drive",
                ],
            )
            docs_service = build("docs", "v1", credentials=creds)
            drive_service = build("drive", "v3", credentials=creds)

            doc = docs_service.documents().create(body={"title": title}).execute()
            doc_id = doc["documentId"]

            # Insert content
            requests = [{"insertText": {"location": {"index": 1}, "text": content}}]
            docs_service.documents().batchUpdate(
                documentId=doc_id, body={"requests": requests}
            ).execute()

            # Make shareable
            drive_service.permissions().create(
                fileId=doc_id,
                body={"type": "anyone", "role": "reader"},
            ).execute()

            # Move to folder if configured
            if settings.google_drive_folder_id:
                drive_service.files().update(
                    fileId=doc_id,
                    addParents=settings.google_drive_folder_id,
                    removeParents="root",
                    fields="id, parents",
                ).execute()

            return f"https://docs.google.com/document/d/{doc_id}/edit"

        except Exception as exc:
            raise IntegrationError(f"Google Docs error: {exc}") from exc
