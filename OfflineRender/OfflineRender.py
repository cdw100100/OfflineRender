import os
import tkinter as tk
from tkinter import messagebox, scrolledtext
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor
import threading

# Define headers globally for all requests
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, Gecko) Chrome/114.0.0.0 Safari/537.36'
}

visited_urls = set()
base_domain = ""
download_folder = ""
total_urls = 0
lock = threading.Lock()

def sanitize_filename(url):
    """Sanitize the URL path to be used as a filename."""
    parsed_url = urlparse(url)
    path = parsed_url.path.strip("/")
    if path.endswith('/'):
        path = path[:-1]
    if not path or parsed_url.path == '/':
        path = "index"
    return f"{path}.html"

def download_asset(asset_url, save_path):
    """Download an asset if it hasn't been visited yet."""
    if asset_url in visited_urls:  # Check if the asset has already been visited
        return
    visited_urls.add(asset_url)  # Mark asset as visited

    try:
        if any(asset_url.endswith(ext) for ext in [".css", ".jpg", ".jpeg", ".png", ".gif", ".svg"]):
            asset_response = requests.get(asset_url, headers=headers)
            asset_response.raise_for_status()

            asset_name = os.path.basename(urlparse(asset_url).path)
            asset_path = os.path.join(save_path, asset_name)

            os.makedirs(save_path, exist_ok=True)

            with open(asset_path, 'wb') as asset_file:
                asset_file.write(asset_response.content)
            log_message(f"Downloaded asset: {asset_url}")
    except Exception as e:
        log_message(f"Failed to download asset {asset_url}: {e}")

def download_page(url, save_path):
    """Download a page and its assets."""
    if url in visited_urls or not url.startswith(base_domain):
        return
    visited_urls.add(url)

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        file_name = sanitize_filename(url)
        page_path = os.path.join(save_path, file_name)

        os.makedirs(os.path.dirname(page_path), exist_ok=True)

        asset_links = []  # Store asset links for later updating
        with ThreadPoolExecutor(max_workers=5) as executor:
            for tag in soup.find_all(['a', 'link', 'img']):
                attr = 'href' if tag.name in ['a', 'link'] else 'src'
                link = tag.get(attr)
                if link:
                    link_url = urljoin(url, link)
                    if link_url.startswith(base_domain):
                        local_link = sanitize_filename(link_url)  # Get local filename
                        asset_links.append((tag, attr, local_link))  # Store the tag, attribute, and local link

                        executor.submit(download_page, link_url, save_path)

                        if tag.name == 'link' and link_url.endswith('.css'):
                            executor.submit(download_asset, link_url, save_path)
                        elif tag.name == 'img':
                            executor.submit(download_asset, link_url, save_path)

        # Update asset links in the soup
        for tag, attr, local_link in asset_links:
            tag[attr] = local_link  # Replace the link with the local filename

        # Save the page
        with open(page_path, 'w', encoding='utf-8') as file:
            file.write(str(soup))
        log_message(f"Downloaded page: {url}")

    except Exception as e:
        log_message(f"Failed to download page {url}: {e}")

def log_message(message):
    """Log messages to the scrolling text box."""
    output_box.configure(state='normal')
    output_box.insert(tk.END, message + '\n')
    output_box.yview(tk.END)  # Scroll to the end
    output_box.configure(state='disabled')

def on_download_click():
    """Start the download process."""
    global visited_urls, base_domain, download_folder, total_urls
    visited_urls = set()
    
    url = url_entry.get()
    if not url:
        messagebox.showerror("Error", "Please enter a URL")
        return
    
    parsed_url = urlparse(url)
    base_domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
    folder_name = parsed_url.netloc.replace('.', '_')
    download_folder = os.path.join(os.getcwd(), folder_name)

    os.makedirs(download_folder, exist_ok=True)
    log_message("Starting download...")

    # Start counting URLs and downloading the homepage in separate threads
    threading.Thread(target=download_page, args=(url, download_folder)).start()

# Set up the GUI
root = tk.Tk()
root.title("Website Downloader")

url_label = tk.Label(root, text="Enter Website URL:")
url_label.pack(pady=5)

url_entry = tk.Entry(root, width=50)
url_entry.pack(pady=5)

download_button = tk.Button(root, text="Download Website", command=on_download_click)
download_button.pack(pady=5)

# Scrolling text box for output messages
output_box = scrolledtext.ScrolledText(root, width=80, height=20, state='disabled')
output_box.pack(pady=10)

root.mainloop()
