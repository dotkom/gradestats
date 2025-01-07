from typing import Optional

import bs4
from .client import Client


class CoursePagesClient(Client):
    USE_ENGLISH_VERSION_FILTERS = [
        "se engelsk versjon",
        "see english version",
        "se engelsk beskrivelse",
        "se engelsk tekst",
        "se engelsk emnebeskrivelse",
        "se engelsk utgave",
        "see engelsk version",
        "see english text",
    ]

    def extract_div_content(self, soup, div_id):
        div = soup.find("div", {"id": div_id})
        if not div:
            return ""

        result = []

        pDelimiter = "\n\n"
        liDelimiter = "\n- "

        for element in div.children:
            if element.name:
                if element.name == "p":
                    result.append(pDelimiter + element.get_text(strip=True))
                elif element.name == "ul" or element.name == "ol":
                    result.extend(
                        liDelimiter + li.get_text(strip=True)
                        for li in element.find_all("li")
                    )
            elif element.string:
                result.append(element.strip())

        return "".join(result).strip()

    def use_english_version(self, text):
        text = text.lower()
        return text.strip() == "" or any(
            use_english_version_filter in text
            for use_english_version_filter in self.USE_ENGLISH_VERSION_FILTERS
        )

    def extract_course_name(self, soup):
        name_raw = soup.title.get_text().split("-")

        if len(name_raw) <= 4:
            return name_raw[1][1 : len(name_raw[1]) - 1]

        name = name_raw[1][1 : len(name_raw[1])]
        for i in range(2, len(name_raw) - 4):
            name += "-"
            name += name_raw[i]
        name += "-"
        name += name_raw[len(name_raw) - 3][0 : len(name_raw[len(name_raw) - 3]) - 1]

        return name

    def extract_has_digital_exam(self, soup):
        om_eksamen: Optional[bs4.element.Tag] = soup.find(attrs={"id": "omEksamen"})
        if om_eksamen is None:
            return False

        dl: Optional[bs4.element.Tag] = om_eksamen.find("dl")
        if dl is None:
            return False

        for dt in dl.find_all("dt"):
            term: Optional[bs4.element.Tag] = dt.find(class_="exam-term")
            if term is None:
                continue

            system: Optional[bs4.element.Tag] = dt.find(class_="exam-system")

            if system.text.strip() == "INSPERA":
                return True

        return False

    @staticmethod
    def get_study_level_from_description(description: str):
        if description == "Doktorgrads nivå":
            return 900
        elif description == "Videreutdanning lavere grad":
            return 800
        elif description == "Høyere grads nivå":
            return 500
        elif description == "Fjerdeårsemner, nivå IV":
            return 400
        elif description == "Tredjeårsemner, nivå III":
            return 300
        elif description == "Videregående emner, nivå II":
            return 200
        elif description == "Grunnleggende emner, nivå I":
            return 100
        elif description == "Lavere grad, redskapskurs":
            return 90
        elif description == "Norsk for internasjonale studenter":
            return 80
        elif description == "Examen facultatum":
            return 71
        elif description == "Examen philosophicum":
            return 70
        elif description == "Forprøve/forkurs":
            return 60
        else:
            return -1

    @staticmethod
    def normalize(string: str):
        return string.replace("\xa0\xc2", " ").replace("\xc2", " ").replace("\xa0", " ")

    def get_course_data(self, code, year: int = None):
        year_segment = ""
        if year:
            year_segment += f"/{str(year)}"

        base_url_no = f"https://www.ntnu.no/studier/emner/{code}{year_segment}"
        data_no = self.requests_retry_session(self.session).get(url=base_url_no)
        text_no = self.normalize(data_no.text)
        soup_no = self.init_soup(text_no)

        no_content_title = "Det finnes ingen informasjon for dette studieåret"
        course_detail_h1 = no_content_title
        try:
            course_detail_h1 = (
                soup_no.find_all("div", {"id": "course-details"})[0]
                .h1.get_text()
                .strip()
            )
        except IndexError:
            print("Something very wrong for course: " + code)

        if course_detail_h1 == no_content_title:
            print(
                f"No info found for course {code}"
                + (f" for year {year}" if year else "")
            )
            return None

        no_longer_taught_text = "Det tilbys ikke lenger undervisning i emnet."
        try:
            strong_text = soup_no.find("div", {"class": "content"}).p.strong.get_text(
                strip=True
            )
            if strong_text == no_longer_taught_text:
                year_info = f" in year {year}" if year else ""
                print(f"Course {code} not taught{year_info}")
                return None
        except Exception:
            pass

        has_digital_exam = self.extract_has_digital_exam(soup_no)

        base_url_eng = f"https://www.ntnu.edu/studies/courses/{code}{year_segment}"
        data_eng = self.requests_retry_session(self.session).get(url=base_url_eng)
        text_eng = self.normalize(data_eng.text)
        soup_eng = self.init_soup(text_eng)

        facts_about_course = ""
        try:
            facts_about_course = (
                soup_no.findAll("div", {"class": "card-body"})[1]
                .p.get_text()
                .split(":")
            )
        except IndexError:
            print("Cannot find facts about course at all, code " + code)

        credit = -1
        try:
            credit = float(facts_about_course[2].split("\n")[2][20:24])
        except:
            print("Not valid number")

        norwegian_name = self.extract_course_name(soup_no)
        english_name = self.extract_course_name(soup_eng)

        if len(facts_about_course) > 3:
            course_level_text = facts_about_course[3].split("\n")[0][
                1 : len(facts_about_course[3].split("\n")[0])
            ]
            study_level = self.get_study_level_from_description(course_level_text)
        else:
            study_level = 0

        last_year_taught = 0
        taught_from = 2008
        taught_in_autumn = False
        taught_in_spring = False
        taught_in_english = False

        place = ""

        try:
            undervisning = soup_no.find_all("div", {"class": "card-body"})[2]
            classes = undervisning.get_text().split("Undervises")
            try:
                place = undervisning.get_text().split("Sted:")[1].strip()
            except IndexError:
                print("Cannot get place")
            for elements in classes:
                if "HØST" in elements:
                    taught_in_autumn = True
                if "VÅR" in elements:
                    taught_in_spring = True
                if "Engelsk" in elements:
                    taught_in_english = True
        except IndexError:
            print("Cannot get undervisning")

        exam_type = ""
        grade_type = ""
        try:
            exam_type_raw = (
                soup_no.find_all("div", {"class": "content-assessment"})[0]
                .p.contents[0]
                .strip()
                .split(":")[1]
            )
            exam_type = exam_type_raw[1 : len(exam_type_raw)]
        except IndexError:
            print("Cannot get exam type")

        try:
            grade_type_raw = (
                soup_no.find_all("div", {"class": "content-assessment"})[0]
                .p.contents[2]
                .strip()
                .split(":")[1]
            )
            grade_type = grade_type_raw[1 : len(grade_type_raw)]
        except IndexError:
            print("Cannot get exam type")

        content = self.extract_div_content(soup_no, "course-content-toggler")
        if self.use_english_version(content):
            content = self.extract_div_content(soup_eng, "course-content-toggler")

        learning_form = self.extract_div_content(soup_no, "learning-method-toggler")
        if self.use_english_version(learning_form):
            learning_form = self.extract_div_content(
                soup_eng, "learning-method-toggler"
            )

        learning_goal = self.extract_div_content(soup_no, "learning-goal-toggler")
        if self.use_english_version(learning_goal):
            learning_goal = self.extract_div_content(soup_eng, "learning-goal-toggler")

        course = {
            "norwegian_name": norwegian_name,
            "english_name": english_name,
            "code": code,
            "credit": credit,
            "study_level": study_level,
            "last_year_taught": last_year_taught,
            "taught_from": taught_from,
            "taught_in_autumn": taught_in_autumn,
            "taught_in_spring": taught_in_spring,
            "taught_in_english": taught_in_english,
            "content": content,
            "learning_form": learning_form,
            "learning_goal": learning_goal,
            "exam_type": exam_type,
            "grade_type": grade_type,
            "place": place,
            "has_had_digital_exam": has_digital_exam,
        }

        return course
