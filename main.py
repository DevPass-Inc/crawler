import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# MySQL 설정
DATABASE_URL = "mysql+pymysql://user:password@localhost:3306/devpass"

engine = create_engine(DATABASE_URL, echo=True)
Session = sessionmaker(bind=engine)
session = Session()

# Selenium 설정
options = webdriver.ChromeOptions()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--disable-gpu')

driver = webdriver.Chrome(options=options)

try:
    url = "https://www.wanted.co.kr/wdlist/518?country=kr&job_sort=job.recommend_order&years=-1&locations=all"
    driver.get(url)

    # 무한 스크롤 처리
    SCROLL_PAUSE_TIME = 2
    last_height = driver.execute_script("return document.body.scrollHeight")

    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(SCROLL_PAUSE_TIME)

        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

    print("스크롤 완료, 모든 데이터를 로드했습니다.")

    job_links = []
    job_cards = driver.find_elements(By.CSS_SELECTOR, ".JobCard_JobCard__Tb7pI a[data-attribute-id='position__click']")
    for card in job_cards:
        job_links.append(card.get_attribute("href"))

    print(f"총 {len(job_links)}개의 채용공고가 있습니다.")

    for link in job_links:
        try:
            driver.get(link)

            try:
                button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, ".JobDescription_JobDescription__paragraph__wrapper__G4CNd button"))
                )
                button.click()
                time.sleep(2)
            except Exception as e:
                print(f"'상세 정보 더 보기' 버튼을 찾을 수 없거나 클릭할 수 없음: {e}")

            company_name = driver.find_element(By.CSS_SELECTOR, ".JobHeader_JobHeader__Tools__Company__Link__zAvYv").text
            location = driver.find_element(By.CSS_SELECTOR, ".JobHeader_JobHeader__Tools__Company__Info__yT4OD").text
            position_name = driver.find_element(By.CSS_SELECTOR, "h1.JobHeader_JobHeader__PositionName__kfauc").text
            experience = driver.find_elements(By.CSS_SELECTOR, ".JobHeader_JobHeader__Tools__Company__Info__yT4OD")[-1].text
            due_date = driver.find_element(By.CSS_SELECTOR, ".JobDueTime_JobDueTime__3yzxa span").text

            job_detail_wrapper = driver.find_element(By.CSS_SELECTOR, ".JobDescription_JobDescription__paragraph__wrapper__G4CNd")
            paragraphs = job_detail_wrapper.find_elements(By.CSS_SELECTOR, ".JobDescription_JobDescription__paragraph__Lhegj")

            details = []
            for paragraph in paragraphs:
                try:
                    content = paragraph.find_element(By.CSS_SELECTOR, "span").text.replace("\n", " ")
                    cleaned_content = content.lstrip("• ").strip()
                    details.append(cleaned_content)
                except Exception as e:
                    print(f"세부정보 읽기 에러: {e}")

            query = text("""
                            INSERT INTO recruitment (company_name, location, position, career, deadline, main_task, qualification, preferred, benefit, recruiting)
                            VALUES (:company_name, :location, :position, :career, :deadline, :main_task, :qualification, :preferred, :benefit, :recruiting)
                        """)
            session.execute(query, {
                "company_name": company_name,
                "location": location,
                "position": position_name,
                "career": experience,
                "deadline": due_date,
                "main_task": details[0] if len(details) > 0 else None,
                "qualification": details[1] if len(details) > 1 else None,
                "preferred": details[2] if len(details) > 2 else None,
                "benefit": details[3] if len(details) > 3 else None,
                "recruiting": details[4] if len(details) > 4 else None
            })
            session.commit()

            print(f"채용 공고 저장 완료: {company_name}, {position_name}")
        except Exception as e:
            print(f"에러 발생: {e}")

finally:
    driver.quit()
    session.close()