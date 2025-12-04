from dataclasses import dataclass

@dataclass
class OfferPayload:
    project_url: str
    amount: int # in euros
    duration: int # in days
    message: str # message to the project owner
    pricing_mode: str = "flat_rate" # "flat_rate" or "daily_rate"
    level: str = "standard"  # "standard" or "super"