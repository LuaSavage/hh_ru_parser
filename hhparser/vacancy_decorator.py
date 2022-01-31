import inflection, re, html2text, codecs, unicodedata
from .scrapper import VacancyScrapper

class Decorator: 
   
    @staticmethod
    def sanitize_string(raw_string):
        raw_string = codecs.encode(str(raw_string),'utf8')
        raw_string = codecs.decode(raw_string,'utf8')
        raw_string = unicodedata.normalize("NFKD", raw_string).rstrip()             
        return re.sub(r'\n','',raw_string)          

    def __field_rename(self, dictonary, new = False, old = False):
        if old in dictonary:
            dictonary[new] = dictonary.pop(old)        
        return dictonary

    def __clear_at_sign (self, row):
        return re.sub(r'^@','', row)

    def __underscore(self, object): 
        if type(object) == list:
            for item in object:
                self.__underscore(item)
            return object
        if type(object) == dict:
            for key in list(object.keys()):
                item = object[key]            
                new_key = inflection.underscore(self.__clear_at_sign(key))
                self.__field_rename(object,new=new_key, old = key)
                if type(item) in [dict, list]:
                    object[new_key] = self.__underscore(item)                
        return object

    def decorate_id (self, vacancy):
        self.__field_rename(vacancy, old = "vacancy_id", new = "id")

    def decorate_url (self, vacancy):
        vacancy["url"] = VacancyScrapper.get_vacancy_url()+"/"+str(vacancy["id"])

    def decorate_salary (self, vacancy):
        self.__field_rename(vacancy, old = "compensation", new = "salary")
        if "salary" in vacancy:
            self.__field_rename(vacancy["salary"], old = "currency_code", new = "currency")
            if not (("from" in vacancy["salary"]) or ("to" in vacancy["salary"])):
                vacancy["salary"] = None

    def decorate_company (self, vacancy):
        self.__field_rename(vacancy,new="employer", old="company")

    def decorate_contacts (self, vacancy):                
        self.__field_rename(vacancy,new="contacts", old="contact_info")

    def decorate_published_at (self, vacancy):                
        vacancy["published_at"] = vacancy["publication_time"]["$"]
        vacancy.pop("publication_time")    
    
    def decorate_type (self, vacancy):                
        if "type" in vacancy:
            vacancy["type"] = {"id": vacancy["type"]}   

    def decorate_schedule (self, vacancy):           
        if "work_schedule" in vacancy:
            vacancy["schedule"] = {
                "id": vacancy.pop("work_schedule")
            }

    def decorate_responses(self, vacancy):
        if "responses_count" in vacancy:
            vacancy["counters"] = {
                "responses": vacancy.pop("responses_count")
            }

    def decorate_description(self, vacancy):
        if "description" not in vacancy:
            vacancy["description"] = str(vacancy["snippet"]["req"]) + str(vacancy["snippet"]["resp"]) + str(vacancy["snippet"]["cond"])
    
    def decorate_key_skills(self, vacancy):
        if "key_skills" not in vacancy:
            vacancy["key_skills"] = vacancy["snippet"]["skill"]

class InterfaceVacancyDecorator:

    def __init__(self, vacancy_data):
        self.vavacancy_data = []
        if type(vacancy_data) == list:
            for vacancy in vacancy_data:
                self.vavacancy_data.append(self.decorate(vacancy))
        elif type(vacancy_data) == dict:
            self.vavacancy_data = self.decorate(vacancy_data)

    def decorate(self, vacancy):
        pass

class SearchedVacancyDecorator(Decorator, InterfaceVacancyDecorator):

    def decorate (self, vacancy):
        self._Decorator__underscore(vacancy)
        self.decorate_id(vacancy) 
        self.decorate_url(vacancy)            
        self.decorate_salary(vacancy)
        self.decorate_contacts(vacancy)
        self.decorate_company(vacancy)
        self.decorate_published_at(vacancy)
        self.decorate_type(vacancy) 
        self.decorate_schedule(vacancy)
        self.decorate_responses(vacancy)
        self.decorate_key_skills(vacancy)
        self.decorate_description(vacancy)        
        return vacancy

class ViewVacancyDecorator(SearchedVacancyDecorator):

    html2text = html2text.HTML2Text()

    def decorate_url (self, vacancy):
        vacancy["url"] = VacancyScrapper.get_vacancy_url()+"/"+str(vacancy["id"])
        vacancy["alternate_url"] = vacancy["url"]
        vacancy["apply_alternate_url"] = "https://hh.ru/applicant/vacancy_response?vacancyId="+str(vacancy["id"])

    def decorate_experiance (self, vacancy):
        self._Decorator__field_rename(vacancy, old = "work_experience", new = "experiance")
        if "experiance" in vacancy:
            vacancy["experiance"] = {"id": vacancy["experiance"]} 

    def decorate_description(self, vacancy):
        if "description" in vacancy:
            self.decorate_branded_description(vacancy)
            self.html2text.ignore_links = True
            vacancy["description"] = self.sanitize_string(
                self.html2text.handle(vacancy["description"]))


    def decorate_branded_description(self, vacancy):
        if "description" in vacancy:
            if "is_branding_preview" in vacancy:
                if vacancy["is_branding_preview"]:
                    vacancy["branded_description"] = vacancy["description"]

    def decorate_published_at (self, vacancy):         
        self._Decorator__field_rename(vacancy, old = "publication_date", new = "published_at")

    def decorate_key_skills(self, vacancy):
        if "key_skills" in vacancy:
            if vacancy["key_skills"]:
                if "key_skill" in vacancy["key_skills"]:
                    vacancy["key_skills"] = vacancy["key_skills"]["key_skill"]

    def decorate_employment (self, vacancy):
        if "employment" in vacancy:
            self._Decorator__field_rename(vacancy["employment"], old = "type", new = "id")

    def decorate(self, vacancy):
        vacancy = super().decorate(vacancy)
        self.decorate_experiance (vacancy)
        self.decorate_employment (vacancy)
        return vacancy