import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path
import uuid
from datetime import datetime, timezone

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Dapil dummy data
dapil_data = [
    {
        "title": "Program Pemberdayaan UMKM Daerah",
        "description": "Implementasi program pemberdayaan UMKM di daerah pemilihan dengan fokus pada peningkatan kapasitas pelaku usaha mikro dan kecil",
        "type": "dapil",
        "value": "Jawa Barat I",
        "region": "Bandung",
        "start_date": "2024-01-15",
        "end_date": "2024-06-30",
        "status": "in_progress"
    },
    {
        "title": "Peningkatan Infrastruktur Desa",
        "description": "Pembangunan dan perbaikan jalan desa serta sarana prasarana pendukung untuk meningkatkan aksesibilitas masyarakat",
        "type": "dapil",
        "value": "Jawa Timur II",
        "region": "Surabaya",
        "start_date": "2024-02-01",
        "end_date": "2024-12-31",
        "status": "in_progress"
    },
    {
        "title": "Bantuan Pendidikan untuk Anak Kurang Mampu",
        "description": "Program beasiswa dan bantuan pendidikan untuk siswa dari keluarga kurang mampu di wilayah dapil",
        "type": "dapil",
        "value": "Jawa Tengah III",
        "region": "Semarang",
        "start_date": "2024-01-10",
        "end_date": "2024-12-20",
        "status": "implemented"
    },
    {
        "title": "Sosialisasi Program Kesehatan Masyarakat",
        "description": "Kegiatan sosialisasi dan edukasi kesehatan untuk meningkatkan kesadaran masyarakat tentang pola hidup sehat",
        "type": "dapil",
        "value": "Sumatra Utara I",
        "region": "Medan",
        "start_date": "2024-03-01",
        "end_date": "2024-05-31",
        "status": "pending"
    },
    {
        "title": "Pengembangan Potensi Wisata Lokal",
        "description": "Program pengembangan destinasi wisata lokal untuk meningkatkan perekonomian masyarakat melalui sektor pariwisata",
        "type": "dapil",
        "value": "Bali I",
        "region": "Denpasar",
        "start_date": "2024-02-15",
        "end_date": "2024-11-30",
        "status": "in_progress"
    }
]

async def load_dapil_data():
    """Load Dapil dummy data into MongoDB"""
    print("Starting Dapil data load...")
    
    # Clear existing dapil directives
    result = await db.directives.delete_many({"type": "dapil"})
    print(f"Deleted {result.deleted_count} existing dapil directives")
    
    # Insert new data
    inserted_count = 0
    for item in dapil_data:
        directive = {
            "id": str(uuid.uuid4()),
            **item,
            "attachments": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.directives.insert_one(directive)
        inserted_count += 1
        print(f"  ✓ Inserted: {item['title']}")
    
    print(f"\n✅ Successfully inserted {inserted_count} dapil directives")
    print("Dapil data load complete!")

if __name__ == "__main__":
    asyncio.run(load_dapil_data())
