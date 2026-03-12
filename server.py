from fastapi import FastAPI, APIRouter, HTTPException, File, UploadFile, Form
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone
import base64
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib import colors

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Models
class FileAttachment(BaseModel):
    filename: str
    content_type: str
    data: str  # base64 encoded
    size: int

class Directive(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: Optional[str] = None
    description: Optional[str] = None
    status: str = "pending"  # "in_progress", "implemented", "pending"
    type: str  # "kementerian" or "dapil"
    value: Optional[str] = None  # The actual value (e.g., "Kementerian PUPR" or "Jawa Barat I")
    region: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    
    # New fields for Kementerian
    tanggal_masuk_surat: Optional[str] = None
    tanggal_surat: Optional[str] = None
    nomor_surat: Optional[str] = None
    asal_surat: Optional[str] = None
    disposisi: Optional[str] = None
    tempat: Optional[str] = None
    acara: Optional[str] = None
    waktu: Optional[str] = None
    contact_person: Optional[str] = None
    pic: Optional[str] = None
    
    # New field for Dapil
    tujuan_program: Optional[str] = None
    
    attachments: List[FileAttachment] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class DirectiveCreate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: str = "pending"
    type: str  # "kementerian" or "dapil"
    value: Optional[str] = None
    region: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    
    # New fields for Kementerian
    tanggal_masuk_surat: Optional[str] = None
    tanggal_surat: Optional[str] = None
    nomor_surat: Optional[str] = None
    asal_surat: Optional[str] = None
    disposisi: Optional[str] = None
    tempat: Optional[str] = None
    acara: Optional[str] = None
    waktu: Optional[str] = None
    contact_person: Optional[str] = None
    pic: Optional[str] = None
    
    # New field for Dapil
    tujuan_program: Optional[str] = None

class DirectiveUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    type: Optional[str] = None
    value: Optional[str] = None
    region: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    
    # New fields for Kementerian
    tanggal_masuk_surat: Optional[str] = None
    tanggal_surat: Optional[str] = None
    nomor_surat: Optional[str] = None
    asal_surat: Optional[str] = None
    disposisi: Optional[str] = None
    tempat: Optional[str] = None
    acara: Optional[str] = None
    waktu: Optional[str] = None
    contact_person: Optional[str] = None
    pic: Optional[str] = None
    
    # New field for Dapil
    tujuan_program: Optional[str] = None

class StatusUpdate(BaseModel):
    status: str

class LoginRequest(BaseModel):
    password: str

class LoginResponse(BaseModel):
    success: bool
    message: str

class Stats(BaseModel):
    total_directives: int
    in_progress: int
    implemented: int
    pending: int
    total_regions: int

# Auth endpoint
@api_router.post("/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    # Simple password check
    admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
    if request.password == admin_password:
        return LoginResponse(success=True, message="Login berhasil")
    raise HTTPException(status_code=401, detail="Password salah")

# Directives endpoints
@api_router.get("/directives", response_model=List[Directive])
async def get_directives(
    type: Optional[str] = None,
    value: Optional[str] = None,
    status: Optional[str] = None
):
    query = {}
    if type:
        query["type"] = type
    if value:
        query["value"] = value
    if status:
        query["status"] = status
    
    # Fetch directives with sorting: newest first (by tanggal_masuk_surat for kementerian, created_at as fallback)
    directives = await db.directives.find(query, {"_id": 0}).to_list(1000)
    
    # Sort: for kementerian, sort by tanggal_masuk_surat DESC, then by created_at DESC
    def sort_key(d):
        if d.get('type') == 'kementerian' and d.get('tanggal_masuk_surat'):
            try:
                # Parse Indonesian date format "DD MMMM YYYY"
                date_str = d.get('tanggal_masuk_surat', '')
                # Try to parse various date formats
                for fmt in ['%d %B %Y', '%d/%m/%Y', '%Y-%m-%d']:
                    try:
                        parsed_date = datetime.strptime(date_str, fmt)
                        return parsed_date
                    except:
                        continue
            except:
                pass
        # Fallback to created_at
        created = d.get('created_at')
        if isinstance(created, str):
            dt = datetime.fromisoformat(created)
            # Make timezone-naive for comparison
            return dt.replace(tzinfo=None) if dt.tzinfo else dt
        if created:
            # Make timezone-naive for comparison
            return created.replace(tzinfo=None) if hasattr(created, 'tzinfo') and created.tzinfo else created
        return datetime.min
    
    directives.sort(key=sort_key, reverse=True)
    
    for directive in directives:
        if isinstance(directive.get('created_at'), str):
            directive['created_at'] = datetime.fromisoformat(directive['created_at'])
        if isinstance(directive.get('updated_at'), str):
            directive['updated_at'] = datetime.fromisoformat(directive['updated_at'])
    return directives

@api_router.get("/directives/export-pdf")
async def export_directives_pdf(type: Optional[str] = None):
    """Export directives to PDF"""
    try:
        query = {}
        if type:
            query["type"] = type
        
        directives = await db.directives.find(query, {"_id": 0}).to_list(1000)
        
        # Create PDF in memory
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
        
        # Container for PDF elements
        elements = []
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1e293b'),
            spaceAfter=20,
            alignment=1  # Center
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=12,
            textColor=colors.HexColor('#059669'),
            spaceAfter=10
        )
        
        normal_style = styles['Normal']
        normal_style.fontSize = 9
        
        # Title
        title = Paragraph(f"Daftar Arahan {type.title() if type else 'Semua'}", title_style)
        elements.append(title)
        elements.append(Spacer(1, 0.5*cm))
        
        # Process each directive
        for idx, directive in enumerate(directives, 1):
            # Directive header
            if directive.get('type') == 'kementerian':
                header = f"{idx}. {directive.get('nomor_surat', 'No Number')}"
            else:
                header = f"{idx}. {directive.get('title', 'No Title')}"
            
            elements.append(Paragraph(header, heading_style))
            
            # Create data table
            data = []
            
            if directive.get('type') == 'kementerian':
                # Kementerian fields
                if directive.get('tanggal_masuk_surat'):
                    data.append(['Tanggal Masuk Surat', directive['tanggal_masuk_surat']])
                if directive.get('tanggal_surat'):
                    data.append(['Tanggal Surat', directive['tanggal_surat']])
                if directive.get('asal_surat'):
                    data.append(['Asal Surat', directive['asal_surat']])
                if directive.get('disposisi'):
                    data.append(['Disposisi', directive['disposisi']])
                if directive.get('tempat'):
                    data.append(['Tempat', directive['tempat']])
                if directive.get('acara'):
                    data.append(['Acara', directive['acara']])
                if directive.get('waktu'):
                    data.append(['Waktu', directive['waktu']])
                if directive.get('contact_person'):
                    data.append(['Contact Person', directive['contact_person']])
                if directive.get('pic'):
                    data.append(['PIC', directive['pic']])
                if directive.get('region'):
                    data.append(['Daerah', directive['region']])
            else:
                # Dapil fields
                if directive.get('tujuan_program'):
                    data.append(['Tujuan Program', directive['tujuan_program']])
                if directive.get('description'):
                    data.append(['Deskripsi', directive['description']])
                if directive.get('value'):
                    data.append(['Dapil', directive['value']])
                if directive.get('region'):
                    data.append(['Daerah', directive['region']])
                if directive.get('start_date'):
                    data.append(['Tanggal Mulai', directive['start_date']])
                if directive.get('end_date'):
                    data.append(['Tanggal Selesai', directive['end_date']])
            
            # Status
            status_map = {
                'pending': 'Menunggu',
                'in_progress': 'Sedang Berjalan',
                'implemented': 'Sudah Dilaksanakan'
            }
            data.append(['Status', status_map.get(directive.get('status'), directive.get('status'))])
            
            if data:
                table = Table(data, colWidths=[4*cm, 12*cm])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f1f5f9')),
                    ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1e293b')),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('TOPPADDING', (0, 0), (-1, -1), 6),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1'))
                ]))
                elements.append(table)
            
            elements.append(Spacer(1, 0.5*cm))
        
        # Build PDF
        doc.build(elements)
        
        # Get PDF from buffer
        buffer.seek(0)
        
        filename = f"arahan_{type if type else 'semua'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating PDF: {str(e)}")

@api_router.get("/directives/{directive_id}", response_model=Directive)
async def get_directive(directive_id: str):
    directive = await db.directives.find_one({"id": directive_id}, {"_id": 0})
    if not directive:
        raise HTTPException(status_code=404, detail="Arahan tidak ditemukan")
    
    if isinstance(directive.get('created_at'), str):
        directive['created_at'] = datetime.fromisoformat(directive['created_at'])
    if isinstance(directive.get('updated_at'), str):
        directive['updated_at'] = datetime.fromisoformat(directive['updated_at'])
    return directive

@api_router.post("/directives", response_model=Directive)
async def create_directive(directive: DirectiveCreate):
    directive_dict = directive.model_dump()
    directive_obj = Directive(**directive_dict)
    
    doc = directive_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    
    await db.directives.insert_one(doc)
    return directive_obj

@api_router.get("/directives/{directive_id}/export-pdf")
async def export_single_directive_pdf(directive_id: str):
    """Export single directive to PDF"""
    try:
        directive = await db.directives.find_one({"id": directive_id}, {"_id": 0})
        if not directive:
            raise HTTPException(status_code=404, detail="Arahan tidak ditemukan")
        
        # Create PDF in memory
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
        
        # Container for PDF elements
        elements = []
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#1e293b'),
            spaceAfter=15
        )
        
        # Title
        if directive.get('type') == 'kementerian':
            title_text = f"Arahan Kementerian - {directive.get('nomor_surat', 'No Number')}"
        else:
            title_text = f"Arahan Dapil - {directive.get('title', 'No Title')}"
        
        title = Paragraph(title_text, title_style)
        elements.append(title)
        elements.append(Spacer(1, 0.5*cm))
        
        # Create data table
        data = []
        
        if directive.get('type') == 'kementerian':
            # Kementerian fields
            if directive.get('tanggal_masuk_surat'):
                data.append(['Tanggal Masuk Surat', directive['tanggal_masuk_surat']])
            if directive.get('tanggal_surat'):
                data.append(['Tanggal Surat', directive['tanggal_surat']])
            if directive.get('nomor_surat'):
                data.append(['Nomor Surat', directive['nomor_surat']])
            if directive.get('asal_surat'):
                data.append(['Asal Surat', directive['asal_surat']])
            if directive.get('disposisi'):
                data.append(['Disposisi', directive['disposisi']])
            if directive.get('tempat'):
                data.append(['Tempat', directive['tempat']])
            if directive.get('acara'):
                data.append(['Acara', directive['acara']])
            if directive.get('waktu'):
                data.append(['Waktu', directive['waktu']])
            if directive.get('contact_person'):
                data.append(['Contact Person', directive['contact_person']])
            if directive.get('pic'):
                data.append(['PIC', directive['pic']])
            if directive.get('region'):
                data.append(['Daerah', directive['region']])
            if directive.get('description'):
                data.append(['Keterangan', directive['description']])
        else:
            # Dapil fields
            if directive.get('title'):
                data.append(['Judul', directive['title']])
            if directive.get('tujuan_program'):
                data.append(['Tujuan Program', directive['tujuan_program']])
            if directive.get('description'):
                data.append(['Deskripsi', directive['description']])
            if directive.get('value'):
                data.append(['Dapil', directive['value']])
            if directive.get('region'):
                data.append(['Daerah', directive['region']])
            if directive.get('start_date'):
                data.append(['Tanggal Mulai', directive['start_date']])
            if directive.get('end_date'):
                data.append(['Tanggal Selesai', directive['end_date']])
        
        # Status
        status_map = {
            'pending': 'Menunggu',
            'in_progress': 'Sedang Berjalan',
            'implemented': 'Sudah Dilaksanakan'
        }
        data.append(['Status', status_map.get(directive.get('status'), directive.get('status'))])
        
        if data:
            table = Table(data, colWidths=[5*cm, 11*cm])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f1f5f9')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1e293b')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1'))
            ]))
            elements.append(table)
        
        # Build PDF
        doc.build(elements)
        
        # Get PDF from buffer
        buffer.seek(0)
        
        # Create filename
        if directive.get('type') == 'kementerian':
            safe_name = directive.get('nomor_surat', 'unknown').replace('/', '-').replace(' ', '_')
        else:
            safe_name = directive.get('title', 'unknown').replace('/', '-').replace(' ', '_')[:30]
        
        filename = f"arahan_{safe_name}_{datetime.now().strftime('%Y%m%d')}.pdf"
        
        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating PDF: {str(e)}")

@api_router.put("/directives/{directive_id}", response_model=Directive)
async def update_directive(directive_id: str, update: DirectiveUpdate):
    existing = await db.directives.find_one({"id": directive_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Arahan tidak ditemukan")
    
    update_data = {k: v for k, v in update.model_dump().items() if v is not None}
    update_data['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    await db.directives.update_one({"id": directive_id}, {"$set": update_data})
    
    updated = await db.directives.find_one({"id": directive_id}, {"_id": 0})
    if isinstance(updated.get('created_at'), str):
        updated['created_at'] = datetime.fromisoformat(updated['created_at'])
    if isinstance(updated.get('updated_at'), str):
        updated['updated_at'] = datetime.fromisoformat(updated['updated_at'])
    return updated

@api_router.patch("/directives/{directive_id}/status", response_model=Directive)
async def update_directive_status(directive_id: str, status_update: StatusUpdate):
    existing = await db.directives.find_one({"id": directive_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Arahan tidak ditemukan")
    
    await db.directives.update_one(
        {"id": directive_id},
        {"$set": {
            "status": status_update.status,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    updated = await db.directives.find_one({"id": directive_id}, {"_id": 0})
    if isinstance(updated.get('created_at'), str):
        updated['created_at'] = datetime.fromisoformat(updated['created_at'])
    if isinstance(updated.get('updated_at'), str):
        updated['updated_at'] = datetime.fromisoformat(updated['updated_at'])
    return updated

@api_router.post("/directives/{directive_id}/attachments")
async def add_attachment(
    directive_id: str,
    file: UploadFile = File(...)
):
    existing = await db.directives.find_one({"id": directive_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Arahan tidak ditemukan")
    
    # Read file and encode to base64
    content = await file.read()
    
    # Validate file size (max 25 MB)
    MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB in bytes
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"Ukuran file melebihi batas maksimal 25 MB. Ukuran file: {len(content) / (1024 * 1024):.1f} MB"
        )
    
    encoded = base64.b64encode(content).decode('utf-8')
    
    attachment = {
        "filename": file.filename,
        "content_type": file.content_type,
        "size": len(content),
        "data": encoded
    }
    
    await db.directives.update_one(
        {"id": directive_id},
        {"$push": {"attachments": attachment}}
    )
    
    return {"message": "File berhasil diupload", "filename": file.filename}

@api_router.delete("/directives/{directive_id}")
async def delete_directive(directive_id: str):
    result = await db.directives.delete_one({"id": directive_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Arahan tidak ditemukan")
    return {"success": True, "message": "Arahan berhasil dihapus"}

# Stats endpoint
@api_router.get("/stats", response_model=Stats)
async def get_stats(
    type: Optional[str] = None,
    value: Optional[str] = None
):
    query = {}
    if type:
        query["type"] = type
    if value:
        query["value"] = value
    
    all_directives = await db.directives.find(query, {"_id": 0}).to_list(1000)
    
    total = len(all_directives)
    in_progress = len([d for d in all_directives if d.get('status') == 'in_progress'])
    implemented = len([d for d in all_directives if d.get('status') == 'implemented'])
    pending = len([d for d in all_directives if d.get('status') == 'pending'])
    
    # Count unique regions
    regions = set(d.get('region') for d in all_directives if d.get('region'))
    
    return Stats(
        total_directives=total,
        in_progress=in_progress,
        implemented=implemented,
        pending=pending,
        total_regions=len(regions)
    )

# Values endpoints
@api_router.get("/values")
async def get_values(type: str):
    query = {"type": type}
    directives = await db.directives.find(query, {"_id": 0, "value": 1}).to_list(1000)
    values = sorted(list(set(d.get('value') for d in directives if d.get('value'))))
    return {"values": values}

@api_router.get("/regions")
async def get_regions():
    directives = await db.directives.find({}, {"_id": 0, "region": 1}).to_list(1000)
    regions = sorted(list(set(d.get('region') for d in directives if d.get('region'))))
    return {"regions": regions}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()