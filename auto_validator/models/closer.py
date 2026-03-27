from pydantic import BaseModel


class Email(BaseModel):
    subject: str
    body_html: str
    body_text: str
    preview_text: str = ""


class PLFSequence(BaseModel):
    email_1_curiosity: Email
    email_2_backstory: Email
    email_3_logic: Email
    email_4_open_cart: Email

    def as_list(self) -> list[Email]:
        return [
            self.email_1_curiosity,
            self.email_2_backstory,
            self.email_3_logic,
            self.email_4_open_cart,
        ]


class CloserOutput(BaseModel):
    thank_you_email: Email
    plf_sequence: PLFSequence | None = None
    launch_approved: bool = False
