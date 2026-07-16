import asyncio
import aiohttp
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import bcrypt
from fastapi import FastAPI, HTTPException, Header, Form, Response, Cookie
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from starlette.requests import Request
from datetime import datetime
from typing import Optional
import os
import json

app = FastAPI(title="SPX Sorting Hub Monitor")

# Lấy đường dẫn thư mục gốc của dự án một cách chính xác trên Vercel
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Cấu hình lại sử dụng đường dẫn tuyệt đối
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

BASE_URL = "https://spx.shopee.vn/api/fleet_order/order/tracking_list/search"

# ================= KẾT NỐI GOOGLE SHEET DATABASE =================
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# Đọc chuỗi JSON cấu hình từ biến môi trường của Vercel
google_creds_raw = os.environ.get("GOOGLE_CREDS_JSON")

if google_creds_raw:
    creds_dict = json.loads(google_creds_raw)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
else:
    # Nếu chạy local dưới máy thì vẫn đọc file như cũ để bạn test
    creds = ServiceAccountCredentials.from_json_keyfile_name(r"C:\Users\...\shopeeapiver2-tbs.json", scope)

client = gspread.authorize(creds)
sheet = client.open_by_key("1__o1Ki_p8JGsOLTpDb5E3vo88dQQ4daY9en7QRONm3U").sheet1

def get_all_users():
    return sheet.get_all_records()

def find_user(username):
    users = get_all_users()
    for u in users:
        if u['username'] == username:
            return u
    return None

def add_user(username, hashed_password, note):
    # Lưu thêm dữ liệu note vào cột thứ 5 (Cột E)
    sheet.append_row([username, hashed_password.decode('utf-8'), 'user', 'pending', note])

def update_user_status(username, status):
    cell = sheet.find(username)
    if cell:
        sheet.update_cell(cell.row, 4, status)

# ================= MAP DANH SÁCH CÁC HUB (Giữ nguyên gốc) =================
ZONE_MAPPING = {
    "vung-tau": {
        "label": "60-Vũng Tàu", "icon": "⚓",
        "hubs": {
            2254: "60-BRA Ba Ria 02 Hub", 69: "60-BRA Ba Ria Hub", 5739: "60-BRA Binh Chau Hub",
            2002: "60-BRA Binh Gia Hub", 719: "60-BRA Chau Duc Hub", 1425: "60-BRA Dat Do Hub",
            4651: "60-BRA Kim Long Hub", 1064: "60-BRA Long Dien Hub", 5407: "60-BRA Long Huong Hub",
            2156: "60-BRA Phu My 02 Hub", 198: "60-BRA Phu My Hub", 5784: "60-BRA Phuoc Thang Hub",
            859: "60-BRA Rach Dua Hub", 4262: "60-BRA Suoi Nghe Hub", 5052: "60-BRA Tam An Hub",
            5738: "60-BRA Tam Thang Hub", 1744: "60-BRA Tan Hai Hub", 5794: "60-BRA Toc Tien Hub",
            2081: "60-BRA Vung Tau 02 Hub", 3958: "60-BRA Vung Tau 03 Hub", 64: "60-BRA Vung Tau Hub",
            2164: "60-BRA Xuyen Moc 02 Hub", 713: "60-BRA Xuyen Moc Hub"
        }
    },
    "dong-nai": {
        "label": "61-Đồng Nai", "icon": "🦌",
        "hubs": {
            4942: "61-DNI An Phuoc Hub", 2326: "61-DNI Bien Hoa 02 Hub", 2438: "61-DNI Bien Hoa 03 Hub",
            2432: "61-DNI Bien Hoa 04 Hub", 2309: "61-DNI Bien Hoa Hub", 831: "61-DNI Buu Long Hub",
            963: "61-DNI Cam My Hub", 5458: "61-DNI Dai Phuoc Hub", 1517: "61-DNI Dau Giay Hub",
            2270: "61-DNI Dinh Quan 02 Hub", 404: "61-DNI Dinh Quan Hub", 5513: "61-DNI Hiep Phuoc Hub",
            830: "61-DNI Hoa An Hub", 49: "61-DNI Long Binh Hub", 1309: "61-DNI Long Binh Tan Hub",
            2280: "61-DNI Long Khanh 02 Hub", 326: "61-DNI Long Khanh Hub", 4954: "61-DNI Long Phuoc Hub",
            978: "61-DNI Long Thanh 02 Hub", 2271: "61-DNI Long Thanh 03 Hub", 138: "61-DNI Long Thanh Hub",
            2207: "61-DNI Long Tho Hub", 5979: "61-DNI Ngoc Dinh Hub", 178: "61-DNI Nhon Trach Hub",
            5460: "61-DNI Phu Binh Hub", 5405: "61-DNI Phu Hoi Hub", 1764: "61-DNI Phu Thanh Hub",
            1505: "61-DNI Phuoc Tan Hub", 5406: "61-DNI Song Ray Hub", 1522: "61-DNI Tam Phuoc Hub",
            5005: "61-DNI Tan Bien 02 Hub", 2037: "61-DNI Tan Bien Hub", 5668: "61-DNI Tan Mai Hub",
            1028: "61-DNI Tan Phong Hub", 723: "61-DNI Tan Phu Hub", 407: "61-DNI Thong Nhat Hub",
            2202: "61-DNI Trang Bom 02 Hub", 2269: "61-DNI Trang Bom 03 Hub", 287: "61-DNI Trang Bom Hub",
            466: "61-DNI Trang Dai Hub", 542: "61-DNI Vinh Cuu Hub", 4258: "61-DNI Xuan Hung Hub",
            2433: "61-DNI Xuan Loc 02 Hub", 285: "61-DNI Xuan Loc Hub"
        }
    },
    "binh-duong": {
        "label": "63-Bình Dương", "icon": "🏭",
        "hubs": {
            3954: "63-BDG An Dien Hub", 5409: "63-BDG An Phu Hub", 1700: "63-BDG An Tay Hub",
            1167: "63-BDG Bac Tan Uyen Hub", 877: "63-BDG Bau Bang Hub", 1106: "63-BDG Ben Cat 02 Hub",
            2307: "63-BDG Ben Cat 03 Hub", 414: "63-BDG Ben Cat Hub", 5053: "63-BDG Binh An Hub",
            5817: "63-BDG Binh Giao Hub", 1514: "63-BDG Binh Hard Hub", 5816: "63-BDG Binh Nham Hub",
            988: "63-BDG Dau Tieng Hub", 2047: "63-BDG Di An 02 Hub", 2308: "63-BDG Di An 03 Hub",
            2893: "63-BDG Di An 04 Hub", 3898: "63-BDG Di An 05 Hub", 51: "63-BDG Di An Hub",
            5511: "63-BDG Dinh Hoa Hub", 4652: "63-BDG Dong An Hub", 5788: "63-BDG Dong Hoa 02 Hub",
            5524: "63-BDG Hoi Nghia Hub", 538: "63-BDG Lai Thieu Hub", 851: "63-BDG Phu Giao Hub",
            4259: "63-BDG Phu Loi Hub", 986: "63-BDG Phu Tan Hub", 5736: "63-BDG Phuoc Hoa Hub",
            2519: "63-BDG Tan Dinh Hub", 540: "63-BDG Tan Dong Hiep Hub", 2048: "63-BDG Tan Uyen 02 Hub",
            2449: "63-BDG Tan Uyen 03 Hub", 3899: "63-BDG Tan Uyen 04 Hub", 188: "63-BDG Tan Uyen Hub",
            4155: "63-BDG Thoi Hoa Hub", 2082: "63-BDG Thu Dau Mot 02 Hub", 2165: "63-BDG Thu Dau Mot 03 Hub",
            45: "63-BDG Thu Dau Mot Hub", 2391: "63-BDG Thuan An 02 Hub", 2215: "63-BDG Thuan An 03 Hub",
            2390: "63-BDG Thuan An 04 Hub", 3955: "63-BDG Thuan An 05 Hub", 47: "63-BDG Thuan An Hub",
            1515: "63-BDG Tuong Binh Hiep Hub"
        }
    },
    "binh-thuan": {
        "label": "62-Bình Thuận", "icon": "🏖️",
        "hubs": {
            818: "62-BTN Bac Binh Hub", 5818: "62-BTN Binh Hung Hub", 1120: "62-BTN Duc Linh Hub",
            1261: "62-BTN Ham Tan Hub", 5797: "62-BTN Ham Thang Hub", 879: "62-BTN Ham Thuan Bac Hub",
            710: "62-BTN Ham Thuan Nam Hub", 3959: "62-BTN Hoai Duc Hub", 5004: "62-BTN Ke Ga Hub",
            172: "62-BTN La Gi Hub", 862: "62-BTN Mui Ne Hub", 1519: "62-BTN Phan Ri Cua Hub",
            977: "62-BTN Phan Thiet 02 Hub", 2206: "62-BTN Phan Thiet 03 Hub", 170: "62-BTN Phan Thiet Hub",
            1439: "62-BTN Phu Quy Hub", 1364: "62-BTN Tanh Linh Hub", 273: "62-BTN Tuy Phong Hub"
        }
    },
    "binh-phuoc": {
        "label": "64-Bình Phước", "icon": "🌿",
        "hubs": {
            1264: "64-BPC Binh Long Hub", 3901: "64-BPC Bu Dang 02 Hub", 4264: "64-BPC Bu Dang 03 Hub",
            853: "64-BPC Bu Dang Hub", 1421: "64-BPC Bu Dop Hub", 1512: "64-BPC Bu Gia Map Hub",
            2312: "64-BPC Chon Thanh 02 Hub", 520: "64-BPC Chon Thanh Hub", 4260: "64-BPC Da Kia Hub",
            1147: "64-BPC Dong Phu Hub", 2201: "64-BPC Dong Xoai 02 Hub", 186: "64-BPC Dong Xoai Hub",
            1507: "64-BPC Hon Quan Hub", 1168: "64-BPC Loc Ninh Hub", 4261: "64-BPC Loc Tan Hub",
            4671: "64-BPC Minh Lap Hub", 4156: "64-BPC Phu Rieng 02 Hub", 1263: "64-BPC Phu Rieng Hub",
            1191: "64-BPC Phuoc Long Hub", 4672: "64-BPC Phuoc Tin Hub"
        }
    },
    "tay-ninh": {
        "label": "65-Tây Ninh", "icon": "🏔️",
        "hubs": {
            5939: "65-TNH An Hoa Hub", 2401: "65-TNH Ben Cau 02 Hub", 1509: "65-TNH Ben Cau Hub",
            3960: "65-TNH Cau Khoi 02 Hub", 965: "65-TNH Cau Khoi Hub", 658: "65-TNH Chau Thanh Hub",
            2310: "65-TNH Go Dau 02 Hub", 711: "65-TNH Go Dau Hub", 4663: "65-TNH Hiep Thanh Hub",
            2520: "65-TNH Hoa Thanh 02 Hub", 1036: "65-TNH Hoa Thanh Hub", 3961: "65-TNH Ninh Son Hub",
            2311: "65-TNH Tan Bien 02 Hub", 1159: "65-TNH Tan Bien Hub", 3998: "65-TNH Tan Chau 02 Hub",
            1103: "65-TNH Tan Chau Hub", 1051: "65-TNH Tay Ninh 02 Hub", 2049: "65-TNH Tay Ninh 03 Hub",
            184: "65-TNH Tay Ninh Hub", 2392: "65-TNH Trang Bang 02 Hub", 1104: "65-TNH Trang Bang Hub"
        }
    },
    "transit": {
        "label": "Transit SOC", "icon": "🚚",
        "hubs": {
            1707: "HCM Mega SOC", 139: "SW SOC", 6: "HN SOC",
            1701: "BN A Mega SOC", 1959: "BN B Mega SOC", 4110: "BD B Mega SOC"
        }
    },
    "central": {
        "label": "Central SOC", "icon": "🎯",
        "hubs": {
            1467: "Gia Nghia SOC", 725: "Buon Ma Thuot SOC", 1030: "Pleiku SOC",
            1769: "Kon Tum SOC", 672: "Dong Hoi SOC", 834: "Cam Xuyen SOC",
            549: "Vinh SOC", 1579: "Phan Rang SOC", 288: "Dien Khanh SOC",
            1791: "Tuy Hoa SOC", 1333: "Quang Ngai SOC", 1041: "Duc Trong SOC",
            3983: "DN Mega SOC", 324: "Tuy Phuoc SOC"
        }
    }
}
STATUS_MAP = [{"status": "8,58,630,631,33,60", "key": "warehouse"}, {"status": "630", "key": "yard"}]

class CookiePayload(BaseModel):
    cookie: str

# ================= TRUNG GIAN BẢO MẬT (AUTH MIDDLEWARE) =================
# Tự động chặn mọi request nếu chưa đăng nhập (ngoại trừ trang login/register và static)
@app.middleware("http")
async def login_required_middleware(request: Request, call_next):
    path = request.url.path
    public_paths = ["/login", "/register", "/auth/login", "/auth/register", "/static"]
    is_public = any(path.startswith(p) for p in public_paths)
    
    if not is_public:
        session_user = request.cookies.get("session_user")
        if not session_user:
            return RedirectResponse(url="/login?msg=Vui lòng đăng nhập trước!", status_code=303)
            
    response = await call_next(request)
    
    # Thêm dòng này để mọi trang riêng tư (như trang chủ /, /admin) không bao giờ bị trình duyệt lưu cache
    if not is_public:
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        
    return response

# ================= ROUTER AUTH & SESSION =================

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, msg: Optional[str] = None):
    # Nếu đã đăng nhập rồi thì không cho vào trang login nữa, đẩy về trang chủ
    if request.cookies.get("session_user"):
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse(request=request, name="login.html", context={"msg": msg})

@app.post("/auth/login")
async def do_login(username: str = Form(...), password: str = Form(...)):
    user = find_user(username)
    if not user:
        return RedirectResponse(url="/login?msg=Tài khoản không tồn tại!", status_code=303)
    if not bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
        return RedirectResponse(url="/login?msg=Sai mật khẩu!", status_code=303)
    if user['status'] != 'approved':
        return RedirectResponse(url="/login?msg=Tài khoản đang chờ duyệt!", status_code=303)
    
    redirect = RedirectResponse(url="/admin" if user['role'] == 'admin' else "/", status_code=303)
    redirect.set_cookie(key="session_user", value=username, max_age=86400, httponly=True)
    return redirect

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, msg: Optional[str] = None):
    return templates.TemplateResponse(request=request, name="register.html", context={"msg": msg})

@app.post("/auth/register")
async def do_register(username: str = Form(...), password: str = Form(...), note: Optional[str] = Form("")):
    if find_user(username):
        return RedirectResponse(url="/register?msg=Tài khoản đã tồn tại!", status_code=303)
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
    # Truyền thêm tham số note vào hàm add_user
    add_user(username, hashed, note)
    return RedirectResponse(url="/login?msg=Đăng ký thành công! Chờ Admin phê duyệt.", status_code=303)

@app.get("/auth/logout")
async def do_logout():
    # 1. Tạo phản hồi chuyển hướng về trang login
    response = RedirectResponse(url="/login?msg=Đã đăng xuất thành công!", status_code=303)
    
    # 2. Xóa cookie session tận gốc bằng cách đặt đè các tham số bảo mật
    response.delete_cookie(
        key="session_user", 
        path="/", 
        domain=None, 
        httponly=True, 
        samesite="lax"
    )
    
    # 3. Ép trình duyệt KHÔNG ĐƯỢC CACHE trang này (Xóa bỏ bug tải lại trang cũ)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    
    return response

# ================= CÁC ROUTE CHÍNH (Đã được đơn giản hóa nhờ Middleware) =================

@app.get("/", response_class=HTMLResponse)
async def get_index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

# ================= TRANG ADMIN PHÊ DUYỆT =================

@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request, session_user: Optional[str] = Cookie(None)):
    if not session_user:
        return RedirectResponse(url="/login", status_code=303)
    admin_check = find_user(session_user)
    if not admin_check or admin_check['role'] != 'admin':
        return HTMLResponse("Quyền truy cập bị từ chối!", status_code=403)
        
    all_users = get_all_users()
    for u in all_users: u['password'] = ""
    return templates.TemplateResponse(request=request, name="admin.html", context={"users": all_users, "admin_name": session_user})

@app.post("/admin/approve/{target_username}")
async def approve_user(target_username: str, session_user: Optional[str] = Cookie(None)):
    if not session_user or find_user(session_user)['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Không có quyền")
    update_user_status(target_username, 'approved')
    return {"status": "success"}

@app.post("/admin/reject/{target_username}")
async def reject_user(target_username: str, session_user: Optional[str] = Cookie(None)):
    if not session_user or find_user(session_user)['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Không có quyền")
    update_user_status(target_username, 'rejected')
    return {"status": "success"}

# ================= CORE ENGINE (GIỮ NGUYÊN GỐC 100%) =================

async def fetch_one(session, hub_id, hub_name, status_cfg, cookie, semaphore):
    url = f"{BASE_URL}?count=24&current_station_ids=2490&page_no=1&order_status={status_cfg['status']}&next_station_ids={hub_id}"
    headers = {'Cookie': cookie, 'Content-Type': 'application/json'}
    async with semaphore:
        for attempt in range(3):
            try:
                async with session.get(url, headers=headers, timeout=12) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {"hub_id": hub_id, "hub_name": hub_name, "type": status_cfg["key"], "total": data.get('data', {}).get('total', 0), "success": True}
                    elif response.status == 429:
                        await asyncio.sleep(1.5 * attempt)
            except Exception:
                await asyncio.sleep(0.5)
        return {"hub_id": hub_id, "hub_name": hub_name, "type": status_cfg["key"], "total": 0, "success": False}

@app.get("/", response_class=HTMLResponse)
async def get_index(request: Request, session_user: Optional[str] = Cookie(None)):
    if not session_user:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse(request=request, name="index.html")

@app.post("/api/cookie")
async def validate_cookie(payload: CookiePayload, session_user: Optional[str] = Cookie(None)):
    if not session_user:
        raise HTTPException(status_code=401, detail="Chưa đăng nhập")
    async with aiohttp.ClientSession() as session:
        url = f"{BASE_URL}?count=1&current_station_ids=2490&page_no=1&order_status=630&next_station_ids=3954"
        headers = {'Cookie': payload.cookie}
        try:
            async with session.get(url, headers=headers, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if 'data' in data:
                        return {"valid": True, "length": len(payload.cookie)}
        except Exception:
            pass
    return {"valid": False}

@app.get("/api/data/{tab_key}")
async def get_tab_data(tab_key: str, x_shopee_cookie: Optional[str] = Header(None), session_user: Optional[str] = Cookie(None)):
    if not session_user:
        raise HTTPException(status_code=401, detail="Chưa đăng nhập")
    if not x_shopee_cookie:
        raise HTTPException(status_code=400, detail="Thiếu chuỗi xác thực Shopee Cookie (Header: X-Shopee-Cookie)")
    if tab_key not in ZONE_MAPPING:
        raise HTTPException(status_code=404, detail="Tab khu vực yêu cầu không nằm trong dữ liệu cấu hình")
    
    target_zone = ZONE_MAPPING[tab_key]
    semaphore = asyncio.Semaphore(45)
    tasks = []
    
    async with aiohttp.ClientSession() as session:
        for hub_id, hub_name in target_zone["hubs"].items():
            for status_cfg in STATUS_MAP:
                tasks.append(fetch_one(session, hub_id, hub_name, status_cfg, x_shopee_cookie, semaphore))
        raw_results = await asyncio.gather(*tasks)

    hub_data_map = {}
    error_count = 0
    for r in raw_results:
        h_id = r["hub_id"]
        if h_id not in hub_data_map:
            hub_data_map[h_id] = {"id": h_id, "name": r["hub_name"], "warehouse": 0, "yard": 0, "success": True}
        if not r["success"]:
            hub_data_map[h_id]["success"] = False
            error_count += 1
        hub_data_map[h_id][r["type"]] = r["total"]

    hubs_list = list(hub_data_map.values())
    return {
        "tab_key": tab_key,
        "label": target_zone["label"],
        "icon": target_zone["icon"],
        "hub_count": len(hubs_list),
        "total_warehouse": sum(h["warehouse"] for h in hubs_list),
        "total_yard": sum(h["yard"] for h in hubs_list),
        "error_count": error_count,
        "hubs": hubs_list,
        "last_updated": datetime.now().strftime("%H:%M:%S")
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("index:app", host="127.0.0.1", port=8000, reload=True)