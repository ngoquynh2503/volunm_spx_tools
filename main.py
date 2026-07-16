import asyncio
import aiohttp
from fastapi import FastAPI, HTTPException, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from starlette.requests import Request
from datetime import datetime
from typing import Optional

app = FastAPI(title="SPX Sorting Hub Monitor")

# Cấu hình static files và vị trí thư mục templates hiển thị giao diện
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

BASE_URL = "https://spx.shopee.vn/api/fleet_order/order/tracking_list/search"

# ================= MAP DANH SÁCH CÁC HUB MỚI NHẤT VÀ ĐẦY ĐỦ NHẤT =================
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
            5817: "63-BDG Binh Giao Hub", 1514: "63-BDG Binh Hoa Hub", 5816: "63-BDG Binh Nham Hub",
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

STATUS_MAP = [
    {"status": "8,58,630,631,33,60", "key": "warehouse"},
    {"status": "630", "key": "yard"}
]

class CookiePayload(BaseModel):
    cookie: str

async def fetch_one(session, hub_id, hub_name, status_cfg, cookie, semaphore):
    url = f"{BASE_URL}?count=24&current_station_ids=2490&page_no=1&order_status={status_cfg['status']}&next_station_ids={hub_id}"
    headers = {'Cookie': cookie, 'Content-Type': 'application/json'}
    async with semaphore:
        for attempt in range(3):
            try:
                async with session.get(url, headers=headers, timeout=12) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "hub_id": hub_id, 
                            "hub_name": hub_name, 
                            "type": status_cfg["key"], 
                            "total": data.get('data', {}).get('total', 0), 
                            "success": True
                        }
                    elif response.status == 429:
                        await asyncio.sleep(1.5 * attempt)
            except Exception:
                await asyncio.sleep(0.5)
        return {"hub_id": hub_id, "hub_name": hub_name, "type": status_cfg["key"], "total": 0, "success": False}

@app.get("/", response_class=HTMLResponse)
async def get_index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.post("/api/cookie")
async def validate_cookie(payload: CookiePayload):
    # Xác thực trực tiếp Cookie Client gửi lên bằng cách probe thử 1 hub
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
async def get_tab_data(tab_key: str, x_shopee_cookie: Optional[str] = Header(None)):
    # Bắt buộc Client cung cấp cookie thông qua Custom Request Header
    if not x_shopee_cookie:
        raise HTTPException(status_code=400, detail="Thiếu chuỗi xác thực Shopee Cookie (Header: X-Shopee-Cookie)")
    
    if tab_key not in ZONE_MAPPING:
        raise HTTPException(status_code=404, detail="Tab khu vực yêu cầu không nằm trong dữ liệu cấu hình")
    
    target_zone = ZONE_MAPPING[tab_key]
    semaphore = asyncio.Semaphore(45)  # Hạn chế 45 luồng song song để giữ an toàn cho cookie
    tasks = []
    
    async with aiohttp.ClientSession() as session:
        for hub_id, hub_name in target_zone["hubs"].items():
            for status_cfg in STATUS_MAP:
                tasks.append(fetch_one(session, hub_id, hub_name, status_cfg, x_shopee_cookie, semaphore))
        
        raw_results = await asyncio.gather(*tasks)

    # Tổng hợp dữ liệu phân tích thành cấu trúc bảng ngang
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
    total_warehouse = sum(h["warehouse"] for h in hubs_list)
    total_yard = sum(h["yard"] for h in hubs_list)
    last_updated = datetime.now().strftime("%H:%M:%S")

    return {
        "tab_key": tab_key,
        "label": target_zone["label"],
        "icon": target_zone["icon"],
        "hub_count": len(hubs_list),
        "total_warehouse": total_warehouse,
        "total_yard": total_yard,
        "error_count": error_count,
        "hubs": hubs_list,
        "last_updated": last_updated
    }

if __name__ == "__main__":
    import uvicorn
    # Thực hiện gọi chạy ASGI app thông qua đối tượng Uvicorn thuần module
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)