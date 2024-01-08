from flask import request

from app.config.db import db
from app.models.surveys import Surveys, Pages, Questions, Answers
from app.models.user import Users, Profiles
from app.parsers.parsers import surveyCreateParser, answerSendParser
from flask_jwt_extended import jwt_required, get_current_user
from flask_restful import Resource


class CreateSurvey(Resource):
    @jwt_required()
    def post(self):
        try:
            user = Users.query.filter_by(login=get_current_user()).first()
            if user.role == "b":
                survey = surveyCreateParser.parse_args()
                new_survey = Surveys(title=survey["title"], description=survey["description"],
                                     logoPosition=survey["logoPosition"], value=survey["value"],
                                     pages=[], user_id=user.id)
                db.session.add(new_survey)
                db.session.flush()
                for i in range(len(survey["pages"])):
                    new_page = Pages(name=survey["pages"][i]["page_name"], elements=[],
                                     survey_id=new_survey.id)
                    db.session.add(new_page)
                    db.session.flush()
                    for j in range(len(survey["pages"][i]["elements"])):
                        new_question = Questions(type=survey["pages"][i]["elements"][j]["type"],
                                                 name=survey["pages"][i]["elements"][j]["name"],
                                                 isRequired=survey["pages"][i]["elements"][j].get("isRequired"),
                                                 title=survey["pages"][i]["elements"][j].get("title"),
                                                 placeholder=survey["pages"][i]["elements"][j].get("placeholder"),
                                                 choices=survey["pages"][i]["elements"][j].get("choices"),
                                                 page_id=new_page.id, )
                        db.session.add(new_question)
                db.session.commit()
                return {"msg": "success"}, 201
            else:
                return {"msg": "you dont have permission"}
        except Exception as e:
            return {"msg": f"survey create error {e}"}, 500


class SendAnswers(Resource):
    @jwt_required()
    def post(self, survey_id):
        try:
            user = Users.query.filter_by(login=get_current_user()).first()
            page_lst = Pages.query.filter_by(survey_id=survey_id).all()
            answersRequest = list(request.json.items())
            for page in page_lst:
                question_lst = Questions.query.filter_by(page_id=page.id).all()
                for i in range(len(question_lst)):
                    new_answer = Answers(title=question_lst[i].name, answer=answersRequest[i][1],
                                         question_id=question_lst[i].id, user_id=user.id)
                    db.session.add(new_answer)
            profile = Profiles.query.filter_by(user_id=user.id).first()
            profile.balance += Surveys.query.filter_by(id=survey_id).first().value
            profile.complete_survey += 1
            db.session.commit()
            return {"msg": "answers has been add"}, 200
        except Exception as e:
            return {"msg": f"answers add error {e}"}, 500


class GetSurveys(Resource):
    @jwt_required()
    def get(self, survey_id=None):
        try:
            if survey_id is None:
                surveys_lst = Surveys.query.all()
            else:
                surveys_lst = Surveys.query.filter_by(id=survey_id).all()
            if surveys_lst:
                surveys_dict = {}
                for survey in surveys_lst:
                    creator = Profiles.query.filter_by(user_id=survey.user_id).first()
                    if creator:
                        creator = creator.username
                    surveys_dict[survey.id] = {"title": survey.title, "description": survey.description,
                                               "logoPosition": survey.logoPosition,
                                               "date_creation": survey.date_creation.strftime("%Y-%m-%d %H:%M:%S"),
                                               "value": survey.value,
                                               "pages": [], "user_id": survey.user_id, "creator": creator}
                return surveys_dict, 200
            else:
                return {"msg": "survey is not found"}
        except Exception as e:
            return {"msg": f"getting surveys error {e}"}, 500


class CompleteSurvey(Resource):
    @jwt_required()
    def get(self, survey_id):
        try:
            if survey_id:
                survey_slv = {}
                survey = Surveys.query.filter_by(id=survey_id).first()
                if survey:
                    page = Pages.query.filter_by(survey_id=survey_id).all()
                    for p in page:
                        element = Questions.query.filter_by(page_id=p.id).all()
                        for e in element:
                            p.elements.append(e.serialize())
                        pg_name = {"name": p.name, "elements": p.elements}
                        survey.pages.append(pg_name)
                    survey_slv[survey_id] = {"title": survey.title, "description": survey.description,
                                             "logoPosition": survey.logoPosition,
                                             "date_creation": survey.date_creation.strftime("%Y-%m-%d %H:%M:%S"),
                                             "value": survey.value, "pages": survey.pages}
                    return survey_slv, 200
                else:
                    return {"msg": "id not already exist"}, 400
            else:
                return {"msg": "necessary id"}, 400
        except Exception as e:
            return {"msg": f"get survey for complete error {e}"}, 500

class GetAnswers(Resource):
    @jwt_required()
    def get(self, survey_id=None):
        try:
            user = Users.query.filter_by(login=get_current_user()).first()
            survey = Surveys.query.filter_by(user_id=user.id, id=survey_id).first()
            if user.role == "b" and survey:
                all_users = set((usr.user_id for usr in Answers.query.all()))
                all_answers = []
                for usr_id in all_users:
                    answers_slv = {}
                    for ans in Answers.query.filter_by(user_id=usr_id):
                        answers_slv[ans.title] = ans.answer
                    info_dict = {"username": Profiles.query.filter_by(user_id=usr_id).first().username,
                                 "answers": answers_slv}
                    all_answers.append(info_dict)
                return {"surveyTitle": survey.title, "users_answers": all_answers}, 200
            else:
                return {"msg": "you dont have permission or survey has been exists"}, 400
        except Exception as e:
            return {"msg": f"get answers error {e}"}, 500
