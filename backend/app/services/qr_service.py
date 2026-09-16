from pathlib import Path
import qrcode
from app.core.config import settings

def generate_equipment_qr(equipment_id: int) -> str:
    """为设备生成专属高清一机一码工业二维码并保存，返回相对访问 URL"""
    settings.QR_DIR.mkdir(parents=True, exist_ok=True)
    file_name = f"qr_dev_{equipment_id}.png"
    file_path = settings.QR_DIR / file_name
    
    # 扫码内容为前端直达路由
    qr_data = f"/equipments/{equipment_id}"
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(str(file_path))
    
    return f"/uploads/qrcodes/{file_name}"
