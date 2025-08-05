import time
from app.findExactCoordinates import find_label_coordinates_by_id
from app.assign_address_from_accessPoint import assign_closest_address
from app.db.mongo import collect_panorama

MAX_RETRIES = 5
RETRY_DELAY = 1  # seconds

def wait_for_human_labels(image_id: str):
    for attempt in range(MAX_RETRIES):
        doc = collect_panorama.find_one({"image_id": image_id})
        if doc:
            labels = doc.get("human_labels", [{}])[0].get("labels", [])
            if labels:
                print(f"✅ Found labels after {attempt + 1} attempt(s) for image_id={image_id}")
                return doc
        time.sleep(RETRY_DELAY)
    print(f"❌ Failed to find labels after {MAX_RETRIES} retries for image_id={image_id}")
    return None

def update_labels_and_image_address(image_id: str):
    doc = wait_for_human_labels(image_id)
    if not doc:
        return  # Already logged in wait_for_human_labels

    labels = doc.get("human_labels", [{}])[0].get("labels", [])
    if not labels:
        print(f"⚠️ No labels found in human_labels[0] for image {image_id}")
        return

    updates = []
    first_address = None

    for idx, label in enumerate(labels):
        label_id = label.get("label_id")
        if not label_id:
            continue

        result = find_label_coordinates_by_id(label_id)
        if not result or "geometry" not in result:
            print(f"⚠️ No geometry found for label {label_id}")
            continue

        lon, lat = result["geometry"]["coordinates"]
        address = assign_closest_address(lat, lon)
        updates.append({
            f"human_labels.0.labels.{idx}.exactCoordinates": {"lat": lat, "lng": lon},
            f"human_labels.0.labels.{idx}.address": address
        })

        if not first_address and address:
            first_address = address

    # Apply updates
    for update in updates:
        collect_panorama.update_one({"image_id": image_id}, {"$set": update})

    if first_address:
        collect_panorama.update_one(
            {"image_id": image_id},
            {"$set": {"address": first_address["google_address"]}}
        )

    print(f"✅ Finished updating labels and address for image_id={image_id}")
