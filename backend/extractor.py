import re
from bs4 import BeautifulSoup

def clean_text(text):
    if not text:
        return ""
    return text.strip()

def extract_email(text):
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    match = re.search(email_pattern, text)
    return match.group(0) if match else ""

def extract_phone(text):
    # Basic phone extraction, looks for patterns like (123) 456-7890 or +1 234...
    # This is a bit generous to catch various formats
    phone_pattern = r'(\+?\d{1,4}?[-.\s]?\(?\d{1,3}?\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9})'
    match = re.search(phone_pattern, text)
    return match.group(0).strip() if match else ""

def extract_email_from_website(soup):
    """Extract email from website page HTML with multiple strategies"""
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    
    # Strategy 1: Extract from text content
    text_content = soup.get_text(" ", strip=True)
    emails = re.findall(email_pattern, text_content)
    
    # Strategy 2: Look for mailto links
    mailto_links = soup.find_all('a', href=re.compile(r'^mailto:', re.IGNORECASE))
    for link in mailto_links:
        href = link.get('href', '')
        email_match = re.search(r'mailto:([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', href, re.IGNORECASE)
        if email_match:
            emails.append(email_match.group(1))
    
    # Filter out common false positives
    filtered_emails = []
    for email in emails:
        email_lower = email.lower()
        # Skip common non-email patterns
        if not any(x in email_lower for x in ['example.com', 'test.com', 'your.email', 'email@', 'noreply', 'no-reply', 'donotreply']):
            # Prefer emails from contact/about sections
            if email not in filtered_emails:
                filtered_emails.append(email)
    
    return filtered_emails[0] if filtered_emails else ""

def extract_socials(soup):
    socials = {}
    patterns = {
        'facebook': r'(?:https?:\/\/)?(?:www\.)?facebook\.com\/[a-zA-Z0-9.]+/?',
        'instagram': r'(?:https?:\/\/)?(?:www\.)?instagram\.com\/[a-zA-Z0-9._]+/?',
        'linkedin': r'(?:https?:\/\/)?(?:www\.)?linkedin\.com\/[a-zA-Z0-9._\-/]+/?',
        'twitter': r'(?:https?:\/\/)?(?:www\.)?(?:twitter\.com|x\.com)\/[a-zA-Z0-9._]+/?',
        'youtube': r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/[a-zA-Z0-9._\-/]+/?',
        'tiktok': r'(?:https?:\/\/)?(?:www\.)?tiktok\.com\/@[a-zA-Z0-9._]+/?'
    }
    
    # Get all hrefs from anchor tags
    links = [a.get('href') for a in soup.find_all('a', href=True)]
    
    for platform, pattern in patterns.items():
        for link in links:
             if re.search(pattern, link, re.IGNORECASE):
                socials[platform] = link
                break # Found one, move to next platform
    
    return socials

def parse_business_data(html, url):
    soup = BeautifulSoup(html, 'html.parser')
    text_content = soup.get_text(" ", strip=True) # Full text for regex search
    
    data = {
        'files_url': url,
        'name': "N/A",
        'rating': "N/A",
        'reviews': "0",
        'category': "N/A",
        'address': "N/A",
        'phone': "N/A",
        'website': "N/A",
        'hours': "N/A",
        'email': "N/A",
        'facebook': "N/A",
        'instagram': "N/A",
        'twitter': "N/A",
        'linkedin': "N/A",
        'youtube': "N/A",
        'tiktok': "N/A"
    }

    try:
        # Business Name
        h1 = soup.find('h1')
        if h1:
            data['name'] = clean_text(h1.text)

        # Rating & Reviews
        rating_elem = soup.find(lambda tag: tag.name == "span" and tag.has_attr("aria-label") and "stars" in tag["aria-label"])
        if rating_elem:
           data['rating'] = rating_elem['aria-label'].split(" ")[0]
        
        reviews_elem = soup.find('button', attrs={'aria-label': re.compile(r'reviews')})
        if reviews_elem:
            data['reviews'] = clean_text(reviews_elem.text).replace('(', '').replace(')', '')
        
        # Category
        category_elem = soup.find('button', attrs={'jsaction': re.compile(r'category')})
        if category_elem:
             data['category'] = clean_text(category_elem.text)

        # Address
        address_btn = soup.find('button', attrs={'data-item-id': 'address'})
        if address_btn:
            data['address'] = clean_text(address_btn.get('aria-label', '').replace('Address: ', ''))
        
        # Phone
        phone_btn = soup.find('button', attrs={'data-item-id': re.compile('phone')})
        if phone_btn:
             data['phone'] = clean_text(phone_btn.get('aria-label', '').replace('Phone: ', ''))
        
        # Email
        email_btn = soup.find('button', attrs={'data-item-id': re.compile('email')})
        if email_btn:
            email_text = clean_text(email_btn.get('aria-label', '').replace('Email: ', ''))
            if email_text and '@' in email_text:
                data['email'] = email_text
        
        # Website
        website_btn = soup.find('a', attrs={'data-item-id': 'authority'})
        if website_btn:
            data['website'] = website_btn.get('href')

        # Hours
        hours_div = soup.find('div', attrs={'aria-label': re.compile(r'Hours')})
        if hours_div:
             data['hours'] = hours_div.get('aria-label')

        # Email & Socials - fallback email extraction from text content
        if data['email'] == "N/A":
            found_email = extract_email(text_content)
            if found_email:
                data['email'] = found_email
            
        found_socials = extract_socials(soup)
        data.update(found_socials) # Merge found socials into data dict

    except Exception as e:
        print(f"Error parsing HTML: {e}")

    return data
