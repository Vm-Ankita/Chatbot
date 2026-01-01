import requests
import re
from app.ocr_utils import extract_text_from_image
from app.utils import encode_data

API_URL = "https://preprod.vmedulife.com/api/helpDesk/documentationPublicData.php"

# 🔥 MASTER OCR SWITCH
ENABLE_OCR = True


# -----------------------------
# Helpers
# -----------------------------
def clean_html(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_all_text_fields(obj: dict) -> str:
    """
    Extract ALL meaningful text from any ERP object.
    Future-proof: if ERP adds new text fields, they are auto-included.
    """
    texts = []

    for k, v in obj.items():
        if isinstance(v, str):
            clean = clean_html(v)
            if len(clean) > 10:   # ignore ids, flags, short labels
                texts.append(clean)

    return "\n".join(texts)


# -----------------------------
# Demo point extractor
# -----------------------------
def extract_demo_points(res: dict):
    """
    Extract ALL ERP text + screenshot text (OCR).
    """
    points = []

    data = res.get("data", {})
    if not isinstance(data, dict):
        return points

    for module in data.values():
        sub_modules = module.get("subModuleData", {})
        if not isinstance(sub_modules, dict):
            continue

        for sub in sub_modules.values():
            demo_data = sub.get("demoPointData", {})
            if not isinstance(demo_data, dict):
                continue

            count = 0
            for demo in demo_data.values():
                count += 1
                if count % 50 == 0:
                    print(f"⏳ Processed {count} demo points...")

                # 1️⃣ Extract ALL available ERP text
                text_from_api = extract_all_text_fields(demo)

                # 2️⃣ Decide OCR usage (smart & fast)
                do_ocr = ENABLE_OCR and len(text_from_api) < 120

                image_texts = []

                if do_ocr:
                    image_urls = []

                    # 🔹 FORMAT A: attachmentPath + AttachmentArray
                    attachment_path = demo.get("attachmentPath", "")
                    attachments = demo.get("AttachmentArray", [])

                    if attachment_path and isinstance(attachments, list):
                        for img in attachments[:2]:
                            image_urls.append(f"{attachment_path}/{img}")

                    # 🔹 FORMAT B: image[].imagePath
                    for img in demo.get("image", []):
                        if isinstance(img, dict) and img.get("imagePath"):
                            image_urls.append(img["imagePath"])

                    # 🔹 OCR (limit to 2 images TOTAL)
                    for img_url in image_urls[:2]:
                        ocr_text = extract_text_from_image(img_url)
                        if ocr_text and len(ocr_text) > 20:
                            image_texts.append(ocr_text)

                # 3️⃣ Merge API text + OCR text
                final_text = "\n".join(
                    [text_from_api] + image_texts
                ).strip()

                if len(final_text) > 30:
                    points.append(final_text)

    return points


# -----------------------------
# Module API
# -----------------------------
def normalize_modules(raw):
    modules = []

    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict):
                modules.append({
                    "moduleId": str(item.get("moduleId")),
                    "moduleName": item.get("moduleName", "Unknown Module")
                })

    elif isinstance(raw, dict):
        for v in raw.values():
            if isinstance(v, dict):
                modules.append({
                    "moduleId": str(v.get("moduleId")),
                    "moduleName": v.get("module_name", "Unknown Module")
                })

    return modules


def get_modules():
    r = requests.post(
        API_URL,
        files={
            "GetPMInstituteModuleList": (None, "true"),
            "data": (None, encode_data({}))
        },
        timeout=30
    )
    r.raise_for_status()

    res = r.json()
    raw = res.get("data", res)

    modules = normalize_modules(raw)
    if not modules:
        raise RuntimeError("❌ No modules found")

    return modules


def get_demo_response(module_id):
    try:
        r = requests.post(
            API_URL,
            files={
                "HelpDeskGetModuleWiseDemoPointList": (None, "true"),
                "data": (None, encode_data({"moduleId": str(module_id)}))
            },
            timeout=15
        )

        if r.status_code != 200:
            print(f"⚠️ Skipping module {module_id} (HTTP {r.status_code})")
            return {}

        return r.json()

    except Exception as e:
        print(f"⚠️ Error fetching module {module_id}: {e}")
        return {}


# -----------------------------
# Main collector
# -----------------------------
def collect_documents():
    documents = []
    modules = get_modules()

    print(f"🔍 Found {len(modules)} modules")

    for idx, m in enumerate(modules, start=1):
        module_id = m.get("moduleId")
        module_name = m.get("moduleName", "Unknown Module")

        try:
            res = get_demo_response(module_id)

            if not res or not isinstance(res, dict):
                print(f"⚠️ Skipping module {module_id} (no data)")
                continue

            demo_texts = extract_demo_points(res)

            for text in demo_texts:
                documents.append(
                    f"Module: {module_name}\n{text}"
                )

        except Exception as e:
            print(f"⚠️ Error processing module {module_id}: {e}")
            continue

        if idx % 5 == 0:
            print(f"⏳ Processed {idx}/{len(modules)} modules")

    print(f"✅ Collected {len(documents)} documentation chunks")
    return documents
