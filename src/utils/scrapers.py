import os
import re
import time
import json
import requests

from playwright.sync_api import Playwright
from bs4 import BeautifulSoup

# constants
jobTypes = ["fulltime", "intern", "contract", "any"]
companySize = ["seed", "small", "medium", "large", "any"]
role = ["eng", "product", "design", "any", "science", "sales", "marketing", "support", "operations", "recruiting", "finance", "legal"]

# functions
def scrape_companies(job_type: str, company_size: str, role: str):
    """
    Scrape companies from Workatastartup.com based on job type, company size and role filters.

    Args:
        job_type (str): Type of job posting (fulltime, intern, contract, any)
        company_size (str): Size of company (seed, small, medium, large, any) 
        role (str): Role category (eng, product, design, etc.)

    Returns:
        list: List of dictionaries containing company URLs and names
    """
    try:
        # launch a new browser instance
        browser = Playwright.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        page.goto("https://www.workatastartup.com/")
        page.click("a[href='https://account.ycombinator.com/authenticate?continue=https%3A%2F%2Fwww.workatastartup.com%2F']")
        page.wait_for_selector('#ycid-input')
        page.fill('#ycid-input', os.environ("EMAIL_ID"))
        
        page.wait_for_selector('#password-input')
        page.fill('#password-input', os.environ("PASSWORD"))
        page.click('button[type="submit"]')
        page.wait_for_load_state('networkidle')

        time.sleep(5)

        # construct the job posting url
        job_posting_url = f"https://www.workatastartup.com/companies?companySize={company_size}&demographic=any&hasEquity=any&hasSalary=any&industry=any&interviewProcess=any&jobType={job_type}&layout=list-compact&locations=US&role={role}&sortBy=created_desc&tab=any&usVisaNotRequired=any"
        page.goto(job_posting_url)

        last_height = page.evaluate("document.body.scrollHeight")
        while True:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(2)
            new_height = page.evaluate("document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

        page.wait_for_selector('.directory-list')

        companies_data = page.eval_on_selector_all(".directory-list > div.bg-beige-lighter", """
            (elements) => {
                return elements.map(companyDiv => {
                    const companyLink = companyDiv.querySelector('a[href*="/companies/"]');
                    const companyNameSpan = companyDiv.querySelector('span.company-name');
                    return {
                        company_url: companyLink ? companyLink.href : null,
                        company_name: companyNameSpan ? companyNameSpan.textContent.trim() : null
                    };
                }).filter(company => company.company_url != null);
            }
        """)

        return companies_data

    except Exception as e:
        print(f"Error scraping companies: {str(e)}")
        return []
    finally:
        if 'browser' in locals():
            browser.close()

def scrape_company_details(company_url: str) -> dict:
    """
    Scrapes company details from a given company URL.
    
    Args:
        company_url (str): The URL of the company to scrape
        
    Returns:
        dict: A dictionary containing the scraped company details
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        response = requests.get(company_url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        company_name = soup.title.string.split('|')[0].strip() if soup.title else ''
        
        company_details = {
            'name': company_name,
            'url': company_url,
            'about': '',
            'jobs': [],
            'linkedin_urls': [],
            'founders': []
        }
        
        about_meta = soup.find('meta', {'property': 'og:description'})
        about_div = soup.find('div', {'class': 'hiring_description'})
        about_p = soup.find('div', {'class': 'mb-6'}).find('p') if soup.find('div', {'class': 'mb-6'}) else None
        
        if about_meta:
            company_details['about'] = about_meta.get('content', '').strip()
        elif about_div:
            company_details['about'] = about_div.get_text().strip()
        elif about_p:
            company_details['about'] = about_p.get_text().strip()
        
        # find the profile div
        profile_div = soup.find(lambda tag: tag.name == "div" and 
                                          tag.get('id', '').startswith('FullCompanyProfile-react-component-'))
        
        # extract founder information
        if profile_div:
            try:
                data_page = profile_div.get('data-page', '{}')
                profile_data = json.loads(data_page)
                
                if 'props' in profile_data and 'rawCompany' in profile_data['props']:
                    founders = profile_data['props']['rawCompany'].get('founders', [])
                    founder_names = [f"{founder['first_name']} {founder['last_name']}" for founder in founders]
                    company_details['founders'] = founder_names
            except json.JSONDecodeError:
                print(f"Could not parse JSON data for {company_name}")
            except Exception as e:
                print(f"Error extracting founder data: {str(e)}")
        
        # extract linkedin urls
        if profile_div:
            linkedin_matches = re.findall(r'https?://(?:www\.)?linkedin\.com/(?:company|in)/[^"\'\s&,]+', str(profile_div))
            unique_linkedin_urls = set()
            
            for linkedin_url in linkedin_matches:
                clean_linkedin_url = re.sub(r'["\'].*$', '', linkedin_url)
                clean_linkedin_url = re.sub(r'&quot;.*$', '', clean_linkedin_url)
                unique_linkedin_urls.add(clean_linkedin_url)
            
            company_details['linkedin_urls'] = list(unique_linkedin_urls)
        
        # extract job urls
        job_urls = set(re.findall(r'(?:href=["\']/jobs/[^"\'\s]+|https://[^"\'\s]*/jobs/[^"\'\s]+)', 
                                str(profile_div) if profile_div else str(soup)))
        
        for job_url in job_urls:
            job_url = re.sub(r'^href=["\']', '', job_url)
            
            if job_url.startswith('/jobs/'):
                job_url = f"https://www.workatastartup.com{job_url}"
            
            if re.match(r'https://www.workatastartup.com/jobs/\d+', job_url):
                job_id = re.search(r'jobs/(\d+)', job_url).group(1)
                clean_job_url = f"https://www.workatastartup.com/jobs/{job_id}"
                company_details['jobs'].append(clean_job_url)
        
        return company_details
        
    except Exception as e:
        print(f"Error scraping company details: {str(e)}")
        return None 
    
def scrape_job_details(url: str):
    """
    Scrapes job details from a given job URL.
    
    Args:
        url (str): The URL of the job to scrape

    Returns:
        str: A string containing the job description text
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        job_details = soup.find('div', {'class': 'company-details'})
        
        return job_details.get_text().strip()
    
    except requests.RequestException as e:
        print(f"Error fetching job details: {str(e)}")
    except Exception as e:
        print(f"Error processing job details: {str(e)}")

    
