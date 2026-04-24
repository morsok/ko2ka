from pathlib import Path
import toml
import os
from typing import Optional, List
from pydantic import BaseModel, Field

CONFIG_FILE = Path("config.toml")

class KomgaConfig(BaseModel):
    url: str = Field(..., description="Komga Base URL")
    email: str = Field(..., description="Komga User Email")
    password: str = Field(..., description="Komga User Password")
    media_roots: List[str] = Field(default_factory=list, description="Komga media root paths on disk")

class KavitaConfig(BaseModel):
    url: str = Field(..., description="Kavita Base URL")
    api_key: str = Field(..., description="Kavita API Key")
    media_roots: List[str] = Field(default_factory=list, description="Kavita media root paths on disk")

class AppConfig(BaseModel):
    komga: KomgaConfig
    kavita: KavitaConfig

    @classmethod
    def load(cls, path: str = "config.toml") -> Optional['AppConfig']:
        p = Path(path)
        if not p.exists():
            return None
        try:
            with open(p, "r") as f:
                data = toml.load(f)
            
            # Env var overrides
            if os.getenv("KOMGA_URL"): 
                if "komga" not in data: data["komga"] = {}
                data["komga"]["url"] = os.getenv("KOMGA_URL")
            if os.getenv("KOMGA_EMAIL"): 
                if "komga" not in data: data["komga"] = {}
                data["komga"]["email"] = os.getenv("KOMGA_EMAIL")
            if os.getenv("KOMGA_PASSWORD"): 
                if "komga" not in data: data["komga"] = {}
                data["komga"]["password"] = os.getenv("KOMGA_PASSWORD")
            
            if os.getenv("KAVITA_URL"):
                if "kavita" not in data: data["kavita"] = {}
                data["kavita"]["url"] = os.getenv("KAVITA_URL")
            if os.getenv("KAVITA_API_KEY"):
                if "kavita" not in data: data["kavita"] = {}
                data["kavita"]["api_key"] = os.getenv("KAVITA_API_KEY")
            if os.getenv("KOMGA_MEDIA_ROOTS"):
                if "komga" not in data: data["komga"] = {}
                data["komga"]["media_roots"] = os.getenv("KOMGA_MEDIA_ROOTS", "").split(",")
            if os.getenv("KAVITA_MEDIA_ROOTS"):
                if "kavita" not in data: data["kavita"] = {}
                data["kavita"]["media_roots"] = os.getenv("KAVITA_MEDIA_ROOTS", "").split(",")

            return cls(**data)
        except Exception as e:
            print(f"Error loading config: {e}")
            return None

def create_default_config(path: str = "config.toml"):
    default_content = """
[komga]
url = "http://localhost:8080"
email = "user@example.com"
password = "password"
# media_roots = ["/comics", "/bd"]

[kavita]
url = "http://localhost:5000"
api_key = "YOUR_KAVITA_API_KEY"
# media_roots = ["/kavita/comics", "/kavita/bd"]
"""
    with open(path, "w") as f:
        f.write(default_content.strip())
