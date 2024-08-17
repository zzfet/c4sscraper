import requests
from datetime import datetime
import re
import json
import time
import os
import argparse
import tarfile
import shutil

# Global wait period between queries
WAIT_PERIOD = 2  # seconds

# Session for making requests with headers and cookies
session = requests.Session()

json_headers = {
    "Accept": "application/json",
    "Content-Type": "application/json; charset=utf-8",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
}

image_headers = {
    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.clips4sale.com/",
    "Sec-Ch-Ua": '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "image",
    "Sec-Fetch-Mode": "no-cors",
    "Sec-Fetch-Site": "same-site",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
}

# Add your actual cookie values here
cookies = {
    "iAgreeWithTerms": "true"
}
session.cookies.update(cookies)


def extract_id_and_tag_name(url):
    pattern = r"https://www\.clips4sale\.com/studio/(\d+)/([^/]+)/?"
    match = re.match(pattern, url)
    if match:
        id = match.group(1)
        tag_name = match.group(2)
        return id, tag_name
    else:
        raise ValueError("URL format is incorrect")


def fetch_clips_count(url):
    id, tag_name = extract_id_and_tag_name(url)
    base_url = "https://www.clips4sale.com/studio/{id}/{tag_name}/Cat0-AllCategories/Page1/C4SSort-added_at/Limit24?_data=routes%2F%28%24lang%29.studio.%24id_.%24studioSlug.%24"
    full_url = base_url.format(id=id, tag_name=tag_name)
    response = session.get(full_url, headers=json_headers)

    if response.status_code != 200:
        raise Exception(f"Failed to fetch data: {response.status_code}")

    data = response.json()
    clips_count = data.get('clipsCount')

    return clips_count


def fetch_clips_data(url, page_number):
    id, tag_name = extract_id_and_tag_name(url)
    base_url = "https://www.clips4sale.com/studio/{id}/{tag_name}/Cat0-AllCategories/Page{page_number}/C4SSort-added_at/Limit24?_data=routes%2F%28%24lang%29.studio.%24id_.%24studioSlug.%24"
    full_url = base_url.format(id=id, tag_name=tag_name, page_number=page_number)
    response = session.get(full_url, headers=json_headers)

    if response.status_code != 200:
        raise Exception(f"Failed to fetch data: {response.status_code}")

    data = response.json()

    clips_data = []
    for clip in data['clips']:
        # Reformat dateDisplay
        original_date = clip.get('dateDisplay')
        formatted_date = datetime.strptime(original_date, '%m/%d/%y %I:%M %p').strftime('%Y-%m-%d %H:%M')

        # Extract related categories
        related_categories = [rel['category'] for rel in clip.get('related_category_links', [])]
        related_categories_str = ",".join(related_categories)
        keywords = [rel['keyword'] for rel in clip.get('keyword_links', [])]
        keywords_str = ",".join(keywords)
        image_link = clip.get('cdn_previewlg_link').replace("_b_","_")
        if image_link.startswith("//"):
            image_link = "https:" + image_link
        clip_info = {
            'title': clip.get('title'),
            'link': f"https://www.clips4sale.com{clip.get('link')}",
            'dateDisplay': formatted_date,
            'cdn_previewlg_link': f"{image_link}",  # Fixing the https issue
            'time_minutes': int(clip.get('time_minutes')),  # Ensuring type consistency
            'size_mb': clip.get('size_mb'),
            'description': clip.get('description'),
            'category_name': clip.get('category_name'),
            'related_categories': related_categories,
            'keywords': keywords
        }
        clips_data.append(clip_info)

    return clips_data


def save_image(url, folder_path):
    file_name = os.path.basename(url)
    file_path = os.path.join(folder_path, file_name)

    if os.path.exists(file_path):
        print(f"Image already exists: {file_path}. Skipping download.")
        return

    response = session.get(url, headers=image_headers)
    if response.status_code == 200:
        with open(file_path, 'wb') as f:
            f.write(response.content)
        print(f"Saved image: {file_path}")
    else:
        print(f"Failed to download image: {url}")


def save_clips_to_json(clips_data, tag_name):
    with open(f"{tag_name}.json", 'w', encoding='utf-8') as output_file:
        json.dump(clips_data, output_file, ensure_ascii=False, indent=4)
    print(f"All clips data saved to {tag_name}.json")


def create_tarball(tag_name):
    current_date = datetime.now().strftime("%Y-%m-%d-%H%M")
    tarball_name = f"{tag_name}_{current_date}.tgz"
    with tarfile.open(tarball_name, "w:gz") as tar:
        tar.add(f"{tag_name}.json", arcname=os.path.basename(f"{tag_name}.json"))
        if os.path.exists(f"{tag_name}_thumbs"):
            tar.add(f"{tag_name}_thumbs", arcname=os.path.basename(f"{tag_name}_thumbs"))
    os.remove(f"{tag_name}.json")
    shutil.rmtree(f"{tag_name}_thumbs")
    print(f"Created tarball: {tarball_name}")


def extract_tarball(tag_name):
    tar_files = [f for f in os.listdir() if f.startswith(f"{tag_name}_") and f.endswith(".tgz")]
    if not tar_files:
        return None
    latest_tarball = max(tar_files, key=os.path.getctime)
    with tarfile.open(latest_tarball, "r:gz") as tar:
        tar.extractall()
    print(f"Extracted tarball: {latest_tarball}")
    return latest_tarball


def update_tarball(tag_name, tarball_name):
    current_date = datetime.now().strftime("%Y-%m-%d-%H%M")
    new_tarball_name = f"{tag_name}_{current_date}.tgz"
    with tarfile.open(new_tarball_name, "w:gz") as tar:
        tar.add(f"{tag_name}.json", arcname=os.path.basename(f"{tag_name}.json"))
        if os.path.exists(f"{tag_name}_thumbs"):
            tar.add(f"{tag_name}_thumbs", arcname=os.path.basename(f"{tag_name}_thumbs"))
    os.remove(f"{tag_name}.json")
    shutil.rmtree(f"{tag_name}_thumbs")
    os.remove(tarball_name)
    print(f"Updated tarball: {new_tarball_name}")


def delta_update(url, save_images=False):
    id, tag_name = extract_id_and_tag_name(url)
    if save_images:
        os.makedirs(f"{tag_name}_thumbs", exist_ok=True)
        tarball_name = extract_tarball(tag_name)
    else:
        tarball_name = None

    filename = f"{tag_name}.json"

    if not os.path.exists(filename):
        print(f"No existing JSON file found for {tag_name}. Fetching all data.")
        main(url, save_images)
        return

    with open(filename, 'r', encoding='utf-8') as jsonfile:
        existing_clips = json.load(jsonfile)
        if not existing_clips:
            print(f"Existing JSON file for {tag_name} is empty. Fetching all data.")
            main(url, save_images)
            return
        last_existing_clip = existing_clips[0]  # Assuming the latest clip is the first entry

    all_new_clips = []
    page_number = 1
    found_last_existing_clip = False

    while not found_last_existing_clip:
        new_clips = fetch_clips_data(url, page_number)
        print(f"Fetched page {page_number} with {len(new_clips)} clips")

        for clip in new_clips:
            if (clip['dateDisplay'] == last_existing_clip['dateDisplay'] and
                    clip['cdn_previewlg_link'] == last_existing_clip['cdn_previewlg_link'] and
                    clip['time_minutes'] == int(last_existing_clip['time_minutes']) and
                    clip['size_mb'] == last_existing_clip['size_mb']):
                found_last_existing_clip = True
                print(f"Found last existing clip: {clip['title']} on page {page_number}")
                break
            all_new_clips.append(clip)
            if save_images:
                save_image(clip['cdn_previewlg_link'], f"{tag_name}_thumbs")

        if found_last_existing_clip:
            break

        page_number += 1
        print(f"Moving to page {page_number}")
        time.sleep(WAIT_PERIOD)  # Respectful delay between requests

    if all_new_clips:
        print(f"Found {len(all_new_clips)} new clips. Updating JSON file.")
        # Prepend new clips to existing clips
        updated_clips = all_new_clips + existing_clips
        save_clips_to_json(updated_clips, tag_name)
    else:
        print("No new clips found.")

    if save_images:
        update_tarball(tag_name, tarball_name)
    else:
        print(f"All clips data saved to {tag_name}.json")


def main(url, save_images=False):
    clips_count = fetch_clips_count(url)
    id, tag_name = extract_id_and_tag_name(url)
    total_pages = (clips_count // 20) + 1  # Corrected the calculation to use 20 clips per page

    all_clips_data = []
    for page in range(1, total_pages + 1):
        clips_data = fetch_clips_data(url, page)
        all_clips_data.extend(clips_data)
        print(f"Fetched page {page} of {total_pages}")
        if save_images:
            os.makedirs(f"{tag_name}_thumbs", exist_ok=True)
            for clip in clips_data:
                save_image(clip['cdn_previewlg_link'], f"{tag_name}_thumbs")
        time.sleep(WAIT_PERIOD)  # Adding a delay of WAIT_PERIOD seconds between requests

    save_clips_to_json(all_clips_data, tag_name)

    if save_images:
        create_tarball(tag_name)
    else:
        print(f"All clips data saved to {tag_name}.json")


def process_url_list(file_path, save_images):
    with open(file_path, 'r') as file:
        urls = file.readlines()
    for url in urls:
        url = url.strip()
        if url:
            delta_update(url, save_images)


def get_input(prompt):
    try:
        return input(prompt)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        exit()


def main_interactive():
    url = get_input("Please enter the studio URL: ").strip()
    save_images_input = get_input("Do you wish to save thumbnail images? (Y/N): ").strip().lower()
    save_images = save_images_input in ['y', 'yes']
    delta_update(url, save_images)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape clips data from Clips4Sale studio")
    parser.add_argument("--save-images", "-S", action="store_true", help="Save thumbnail images")
    parser.add_argument("--url-list", "-L", help="Path to a file containing a list of URLs")
    parser.add_argument("url", nargs="?", help="URL of the Clips4Sale studio")

    args = parser.parse_args()

    if args.url_list:
        process_url_list(args.url_list, args.save_images)
    elif args.url:
        delta_update(args.url, args.save_images)
    else:
        main_interactive()
