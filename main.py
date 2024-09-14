from playwright.sync_api import sync_playwright
from dataclasses import dataclass, asdict, field
import pandas as pd
import os
import sys


@dataclass
class GatedCommunity:
    """Holds gated community data."""
    name: str = None
    address: str = None
    latitude: float = None
    longitude: float = None


@dataclass
class GatedCommunityList:
    """Holds a list of GatedCommunity objects and saves them."""
    communities: list[GatedCommunity] = field(default_factory=list)
    save_at = 'output'

    def dataframe(self):
        """Converts communities list to pandas dataframe."""
        return pd.json_normalize(
            (asdict(community) for community in self.communities), sep="_"
        )

    def save_to_excel(self, filename):
        """Saves data to an Excel file."""
        if not os.path.exists(self.save_at):
            os.makedirs(self.save_at)
        self.dataframe().to_excel(f"/Users/uthkarshsingh/Desktop/Ayani/ApartmentsData/{filename}.xlsx", index=False)

    def save_to_csv(self, filename):
        """Saves data to a CSV file."""
        if not os.path.exists(self.save_at):
            os.makedirs(self.save_at)
        self.dataframe().to_csv(f"/Users/uthkarshsingh/Desktop/Ayani/ApartmentsData/{filename}.csv", index=False)

    def contains(self, community: GatedCommunity) -> bool:
        """Checks if a community already exists in the list by name and address."""
        return any(
            c.name == community.name and c.address == community.address
            for c in self.communities
        )


def extract_coordinates_from_url(url: str) -> tuple[float, float]:
    """Extracts coordinates from a Google Maps URL."""
    coordinates = url.split('/@')[-1].split('/')[0]
    return float(coordinates.split(',')[0]), float(coordinates.split(',')[1])


def main():
    # Define the array of pincodes to search for gated communities
    pincodes = ['600119', '600130', '600100', '600096', '600131', '603112', '600129', '600115', '600113', '600102', '600097', '600091']
    
    # Define the array of search queries to search for different types of communities
    search_queries = [
        "gated communities in", "apartment complex in", "Condominium complex in",
        "Residents association in", "Multi-unit residential building in", "villas in",
        "Flats in", "Residential complex in"
    ]

    all_communities_list = []  # This will store all the dataframes to concatenate later

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        page.goto("https://www.google.com/maps", timeout=60000)
        page.wait_for_timeout(5000)

        # Loop through each pincode
        for pincode in pincodes:
            community_list = GatedCommunityList()

            # Loop through each search query
            for search_query in search_queries:
                search_for = f"{search_query} {pincode}"
                print(f"Searching for: {search_for}")

                page.locator('//input[@id="searchboxinput"]').fill(search_for)
                page.keyboard.press("Enter")
                page.wait_for_timeout(5000)

                # Scrolling to load more results
                page.hover('//a[contains(@href, "https://www.google.com/maps/place")]')
                previously_counted = 0

                while True:
                    page.mouse.wheel(0, 10000)
                    page.wait_for_timeout(3000)

                    if page.locator('//a[contains(@href, "https://www.google.com/maps/place")]').count() >= 50:
                        listings = page.locator('//a[contains(@href, "https://www.google.com/maps/place")]').all()[:]
                        listings = [listing.locator("xpath=..") for listing in listings]
                        print(f"Total Scraped: {len(listings)}")
                        break
                    else:
                        if page.locator('//a[contains(@href, "https://www.google.com/maps/place")]').count() == previously_counted:
                            listings = page.locator('//a[contains(@href, "https://www.google.com/maps/place")]').all()
                            print(f"Arrived at all available\nTotal Scraped: {len(listings)}")
                            break
                        else:
                            previously_counted = page.locator('//a[contains(@href, "https://www.google.com/maps/place")]').count()

                for listing in listings:
                    try:
                        listing.click()
                        page.wait_for_timeout(5000)

                        name_xpath = '//h1[@class="DUwDvf lfPIob"]'
                        address_xpath = '//button[@data-item-id="address"]//div[contains(@class, "fontBodyMedium")]'

                        community = GatedCommunity()

                        # Extract name
                        if page.locator(name_xpath).count() > 0:
                            community.name = page.locator(name_xpath).inner_text().strip()
                        else:
                            community.name = "No Name Available"

                        # Extract address
                        if page.locator(address_xpath).count() > 0:
                            community.address = page.locator(address_xpath).inner_text().strip()
                        else:
                            community.address = "No Address Available"

                        # Extract coordinates
                        community.latitude, community.longitude = extract_coordinates_from_url(page.url)

                        # Avoid duplicates before appending
                        if not community_list.contains(community):
                            community_list.communities.append(community)
                        else:
                            print(f"Duplicate found: {community.name}, {community.address}")

                    except Exception as e:
                        print(f'Error occurred: {e}')

            # Save the results for the current pincode
            community_list.save_to_csv(f"gated_communities_{pincode}")
            # Store the dataframe in the list for later concatenation
            all_communities_list.append(community_list.dataframe())

        # Combine all dataframes into a single dataframe and save as a single CSV file
        all_communities_df = pd.concat(all_communities_list, ignore_index=True)
        if not os.path.exists('output'):
            os.makedirs('output')
        all_communities_df.to_csv('output/gated_communities_all.csv', index=False)

        browser.close()


if __name__ == "__main__":
    main()