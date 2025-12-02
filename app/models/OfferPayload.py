from dataclasses import dataclass

@dataclass
class OfferPayload:
    project_url: str
    amount: int # in euros
    pricing_mode: str = "project_rate" # "project_rate" or "daily_rate"
    duration: int # in days
    message: str # message to the project owner
    level: str = "standard"  # "standard" or "super"