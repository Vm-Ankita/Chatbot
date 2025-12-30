import requests
import re
from app.utils import encode_data

API_URL = "https://preprod.vmedulife.com/api/helpDesk/documentationPublicData.php"


# -----------------------------
# Helpers
# -----------------------------
def clean_html(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_demo_points(res: dict):
    """
    Extract demo points from deeply nested ERP structure.
    Returns list of dicts with clean text.
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

            for demo in demo_data.values():
                title = clean_html(demo.get("point", ""))
                desc = clean_html(demo.get("explanation", ""))

                text = "\n".join(t for t in [title, desc] if t)
                if len(text) > 20:
                    points.append(text)

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
    r = requests.post(
        API_URL,
        files={
            "HelpDeskGetModuleWiseDemoPointList": (None, "true"),
            "data": (None, encode_data({"moduleId": str(module_id)}))
        },
        timeout=30
    )
    r.raise_for_status()
    return r.json()


# -----------------------------
# Main collector
# -----------------------------
def collect_documents():
    documents = []
    modules = get_modules()

    print(f"🔍 Found {len(modules)} modules")

    for m in modules:
        module_id = m["moduleId"]
        module_name = m["moduleName"]

        res = get_demo_response(module_id)
        demo_texts = extract_demo_points(res)

        for text in demo_texts:
            documents.append(
                f"""
Module: {module_name}
{text}
"""
            )

    print(f"✅ Collected {len(documents)} documentation chunks")
    return documents
