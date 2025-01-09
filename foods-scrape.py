from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.keys import Keys
import csv
import time
import traceback

wait_time = 2

# Add more locations if needed
foods = [
    "Rice",
    "Seaweed",
]

# Create a new instance of the Chrome driver
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
url = "https://ecatalog.wismettacusa.com/product.php?id=36277&branch=TOR"
driver.get(url)

data = []

for food in foods:
    food_link = WebDriverWait(driver, wait_time).until(
        EC.presence_of_all_elements_located((By.XPATH, f'//a[normalize-space(@title)="{food.upper()}"]'))
    )
    # Scroll the element into view
    driver.execute_script("arguments[0].scrollIntoView(true);", food_link[0])

    # Click the element
    food_link[0].click()

    links = WebDriverWait(driver, wait_time).until(
        EC.presence_of_all_elements_located((By.XPATH, f'//a[normalize-space(@title)="{food.upper()}"]/following-sibling::ul[1]/li/a'))
    )

    for i in range(len(links)):
        links = WebDriverWait(driver, wait_time).until(
            EC.presence_of_all_elements_located((By.XPATH, f'//a[normalize-space(@title)="{food.upper()}"]/following-sibling::ul[1]/li/a'))
        )

        links[i].click()

        # Locate the <select> element using the provided XPath
        dropdown = driver.find_element(By.XPATH, '//*[@id="productNumShow"]')

        # Create a Select object
        select = Select(dropdown)

        # Select the option with value "100"
        select.select_by_value("100")

        num_products = int(WebDriverWait(driver, wait_time).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="product-results"]/span'))
        ).text)

        for j in range(1, num_products + 1):
            # Find all child <div> elements under the first 'product-details' div
            child_divs = driver.find_elements(By.XPATH, f"(//div[@class='product-details'])[{j}]/div")

            # Initialize temporary variables for the first 7 elements
            temp_variables = []

            # Iterate through the first 7 child divs
            for k in range(7):
                child_div = child_divs[k]

                # Check if the <div> contains a <span>
                span = child_div.find_elements(By.XPATH, ".//span")
                
                if span:  # If <span> exists, get its text
                    temp_variables.append(span[0].get_attribute("textContent")) # get_attribute can be used to extract hidden text (not visible on the page)
                else:  # Otherwise, get the <div>'s text
                    temp_variables.append(child_div.text)

            data.append(
                {
                    "Product Name": temp_variables[0],
                    "Brand": temp_variables[1],
                    "Category": temp_variables[2],
                    "Item Number": temp_variables[3],
                    "Pack Size": temp_variables[4],
                    "Minimum Order Qty": temp_variables[5],
                    "Barcode": temp_variables[6],
                }
            )

# Save data to CSV
with open("asian-foods.csv", "w", newline="", encoding="utf-8") as file:
    writer = csv.DictWriter(file, fieldnames=["Product Name", "Brand", "Category", "Item Number", "Pack Size", "Minimum Order Qty", "Barcode"])
    writer.writeheader()  # Write column headers
    writer.writerows(data)  # Write data rows

print("Data saved to asian-foods.csv")

# Close the driver
driver.quit()
