import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path
import uuid
from datetime import datetime, timezone
import json

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Load Excel data from JSON file
with open(ROOT_DIR / 'full_excel_data.json', 'r', encoding='utf-8') as f:
    excel_data = json.load(f)

async def convert_date_format(date_str):
    """Convert Indonesian date format to YYYY-MM-DD"""
    if not date_str or date_str == "null":
        return None
    
    # Mapping Indonesian months to numbers
    months = {
        "Januari": "01", "Februari": "02", "Maret": "03", "April": "04",
        "Mei": "05", "Juni": "06", "Juli": "07", "Agustus": "08",
        "September": "09", "Oktober": "10", "November": "11", "Desember": "12"
    }
    
    try:
        # Parse "DD MMMM YYYY" format
        parts = date_str.split()
        if len(parts) == 3:
            day = parts[0].zfill(2)
            month = months.get(parts[1], "01")
            year = parts[2]
            return f"{year}-{month}-{day}"
    except:
        pass
    
    return None

async def load_data():
    """Load Excel data into MongoDB"""
    print("Starting data load...")
    
    # Clear existing kementerian directives
    result = await db.directives.delete_many({"type": "kementerian"})
    print(f"Deleted {result.deleted_count} existing kementerian directives")
    
    # Insert new data
    inserted_count = 0
    for item in excel_data:
        if not item.get("TANGGAL MASUK SURAT") or not item.get("NOMOR SURAT"):
            continue
            
        # Convert date format
        tanggal_masuk = await convert_date_format(item.get("TANGGAL MASUK SURAT"))
        
        # Normalize disposisi to match our options
        disposisi = item.get("DISPOSISI", "")
        if disposisi:
            if "PPKTrans" in disposisi or "PPKTRANS" in disposisi.upper():
                disposisi = "Dirjen PPKTrans"
            elif "PEMT" in disposisi.upper() or "PEI" in disposisi.upper():
                disposisi = "Dirjen PEMT"
            elif disposisi and disposisi not in ["Dirjen PPKTrans", "Dirjen PEMT"]:
                disposisi = "lainnya"
        
        directive = {
            "id": str(uuid.uuid4()),
            "type": "kementerian",
            "status": "pending",
            "tanggal_masuk_surat": tanggal_masuk or item.get("TANGGAL MASUK SURAT"),
            "nomor_surat": item.get("NOMOR SURAT"),
            "asal_surat": item.get("ASAL SURAT"),
            "disposisi": disposisi if disposisi else "lainnya",
            "tempat": item.get("Tempat"),
            "acara": item.get("Acara"),
            "waktu": item.get("Waktu"),
            "contact_person": item.get("Contact Person"),
            "pic": item.get("PIC"),
            "region": None,
            "description": None,
            "attachments": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.directives.insert_one(directive)
        inserted_count += 1
    
    print(f"Successfully inserted {inserted_count} directives")
    print("Data load complete!")

if __name__ == "__main__":
    asyncio.run(load_data())
