import json
import unicodedata
import inflection

class DumpParser:

    def __init__(self, scrapper = None):
        self.scrapper = scrapper

    def __field_rename(self, dictonary, new = False, old = False):
        if old in dictonary:
            dictonary[new] = dictonary.pop(old)
        return dictonary

    def __underscore(self, object):
        for item in object.items():
            if type(item[1]) != dict:
                object = self.__field_rename(object,new=inflection.underscore(item[0]), old = item[0])
            else:                
                object[item[0]] = self.__underscore(item[1])
        return object

    def parse_template(self,page):
        raw_json = None
        for ch in page.find('noindex').children: raw_json=ch.contents[0] 
        raw_json = json.dumps(json.loads(raw_json), indent=4, ensure_ascii=False) 
        print(raw_json)   
        return json.loads(raw_json) 

    def parse_vacancy_page(self, page):
        json_obj =  self.parse_template(page) 


    def parse_search_page(self, searching_page):    
        json_obj =  self.parse_template(searching_page)
        vacancies = json_obj["vacancySearchResult"]["vacancies"]
        for vacancy in vacancies:
            vacancy["id"] = vacancy.pop("vacancyId")
            vacancy["url"] = self.scrapper.get_base_url()+"/"+str(vacancy["id"])

            if "compensation" in vacancy:
                vacancy["salary"] = vacancy.pop("compensation")

                if "currencyCode" in vacancy["salary"]:
                    vacancy["salary"]["currency"] = vacancy["salary"].pop("currencyCode")

            if not (("from" in vacancy["salary"]) or ("to" in vacancy["salary"])):
                vacancy["salary"] = None

            vacancy = self.__field_rename(vacancy,new="response_letter_required", old="@responseLetterRequired")
            vacancy = self.__field_rename(vacancy,new="employer", old="company")
            vacancy = self.__field_rename(vacancy,new="contacts", old="contactInfo")

            if "publicationTime" in vacancy:
                vacancy["published_at"] = vacancy["publicationTime"]["$"]
                vacancy.pop("publicationTime")    
            if "type" in vacancy:
                vacancy["type"] = {"id": vacancy["type"]}
            if "area" in vacancy:
                vacancy["area"] = self.__field_rename(vacancy["area"],new="id", old="@id")

            if "workSchedule" in vacancy:
                vacancy["schedule"] = {
                    "id": vacancy.pop("workSchedule")
                }
            if "responsesCount" in vacancy:
                vacancy["counters"] = {
                    "responses": vacancy.pop("responsesCount")
                }
            if "key_skills" not in vacancy:
                vacancy["key_skills"] = vacancy["snippet"]["skill"]
            if "description" not in vacancy:
                vacancy["description"] = str(vacancy["snippet"]["req"]) + str(vacancy["snippet"]["resp"]) + str(vacancy["snippet"]["cond"])
            vacancy = self.__underscore(vacancy)    

        vacancies_json = json.dumps(vacancies, indent=4, ensure_ascii=False) 
        print(vacancies_json)
        with open("vacancies_json.json", "w", encoding='utf-8') as file:
            file.write(vacancies_json)      
    








                


            


    def parse(self):
        tmp_page = self.scrapper.get_searching_results_page()
        self.parse_search_page(tmp_page)




    

