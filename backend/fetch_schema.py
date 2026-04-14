import requests
import json
import xml.etree.ElementTree as ET

urls = [
    "16110669", # Weather
    "16110670", # Soil
    "16132920", # Runoff 1
    "16116030", # Water quality
]

output = {}

for dev_id in urls:
    url = f"https://iot.whxph.com:44300/XPHapiv2/data-n/{dev_id}"
    try:
        resp = requests.get(url, verify=False, timeout=5)
        root = ET.fromstring(resp.text)
        
        device_data = []
        for ele in root.findall(".//eleLists"):
            ename_node = ele.find("eName")
            evalue_node = ele.find("eValue")
            eunit_node = ele.find("eUnit")
            
            # eName could be nested inside another eleLists if they have <eleLists><eleLists> structure
            # Looking closely at the XML provided by the user:
            # <eleLists><eleLists><eName>...</eName></eleLists>...
            if ename_node is None:
                continue

            name = ename_node.text
            val = evalue_node.text if evalue_node is not None else ""
            unit = eunit_node.text if eunit_node is not None else ""
            device_data.append(f"{name} ({unit}): {val}")
        
        output[dev_id] = device_data
    except Exception as e:
        output[dev_id] = f"Error: {e}"

for k, v in output.items():
    print(f"Device {k}:")
    if isinstance(v, list):
        for item in v:
            print("  ", item)
    else:
        print("  ", v)
    print("-" * 40)
