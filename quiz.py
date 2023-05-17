


import json
from pprint import pprint
import random
from random import randint
import os
import nltk
from nltk.corpus import wordnet as wn
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import string
import telegram
from telegram.ext import CommandHandler, MessageHandler, Filters, Updater

WUP_Threshold = 0.8
greeting = ['Hi there, how are you doing today!\nI am quizzy, let\'s play a quiz today!', 'Hi I\'m quizzy, your quizmaster!', 'Quizzy here, let\'s start']
wrong_category = ['Hmm! We currently do not have any quizzes on that.', 'Sorry we don\'t have any questions regarding that.', 'Hmm, pick another one!']
next_question = ['Here comes the next question!', 'Get ready for the next one!', 'Here comes another']
correct_answer = ['Correct answer, well done!', 'You\'re smart!', 'You\'re a genius']
wrong_answer = ['Sorry, wrong answer. Nevermind', 'Wrong! Buck up', 'Nah! Come on!']

def extractNounsAndAdjectives(words):
        NJ = []
        pos = nltk.pos_tag(words)
        for word, tag in pos:
                if tag[0] in ('N', 'J'):
                        NJ.append(word)
        return NJ

# Wu-Palmer similarity
def WUPSimilarity(w1, w2):
        w1 = wn.synsets(w1)
        w2 = wn.synsets(w2)
        max_WUP = 0
        # Checking for the first 3 synonyms in order to avoid noise
        for i in range(0, min(3, len(w1))):
                for j in range(0, min(3, len(w2))):
                        sim = w1[i].wup_similarity(w2[j])
                        if sim is not None:
                                max_WUP = max(max_WUP, sim)
        return max_WUP

# Compute possible categories based on user response
def computeCategories(categories, user_response_NJ):
        probable_categories = {}
        for w1 in categories:
                for w2 in user_response_NJ:
                        for w in w1.split('-'):
                                sim = WUPSimilarity(w, w2)
                                # print(w, w2, sim)
                                if sim >= 1:
                                        probable_categories.clear()
                                        probable_categories[w1] = w2
                                        return probable_categories
                                elif sim >= WUP_Threshold:
                                        probable_categories[w1] = w2
        return probable_categories

# Compute the possible choices present in user_response
def computeChoices(user_response, choices):
        # # Use this if you want to confirm for ambiguous user answers
        # uniqueInChoices = []
        # for i in range(0, len(choices)):
        #         unique_choice = nltk.word_tokenize(choices[i].lower())
        #         unique_choice = [i for i in unique_choice if i not in punctuations and i not in stop_words]
        #         unique_choice = set(unique_choice)
        #         for j in range(0, len(choices)):
        #                 if i != j:
        #                         unique_choice = unique_choice - set(nltk.word_tokenize(choices[j].lower()))
        #         uniqueInChoices.append(list(unique_choice))
        punctuations = list(string.punctuation)
        stop_words = set(stopwords.words('english'))
        lemmatizer = WordNetLemmatizer()
        ct = 'a'
        probable_choices = []
        user_response = nltk.word_tokenize(user_response.lower())
        user_response = [lemmatizer.lemmatize(word, pos='v') for word in user_response]
        user_response = [i for i in user_response if i not in punctuations and i not in stop_words]
        user_response = set(user_response)
        for choice in choices:
                # print(choice)
                choice = nltk.word_tokenize(choice.lower())
                choice = [lemmatizer.lemmatize(word, pos='v') for word in choice]
                choice = [i for i in choice if i not in punctuations and i not in stop_words]
                choice = set(choice)
                if len(user_response.intersection(choice)) > 0:
                        probable_choices.append(ct)
                ct = chr(ord(ct) + 1)
        return probable_choices

def displayBotResponse(score, responses, isCorrect, answer_choice=''):
        print(random.choice(responses))
        if isCorrect:
                score += 1
        else:
                score -= 0.25
                print("The correct answer is {}".format(answer_choice.upper()))
        print ('Score = {}'.format(score))
        return score

def loadAllCategories():
        categories = set()
        for root, dirs, files in os.walk("./OpenTriviaQA_JSON"):
                for name in files:
                        categories.add(name[: -5])
        return categories

def chooseCategory():
        categories = loadAllCategories()
        flag = False
        category = ""
        print('What would you liked to be quizzed on?')
        while flag == False:
                user_response = input()
                print()
                if len(user_response) > 0 and user_response[0] == '@':
                        if user_response[1: ] == 'list_quizzes':
                                for c in categories:
                                        print(c)
                                print()
                                continue
                words = nltk.word_tokenize(user_response)
                user_response_NJ = extractNounsAndAdjectives(words)
                probable_categories = computeCategories(categories, user_response_NJ)

                if len(probable_categories) == 0:
                        print("{} Type @list_quizzes to get a list of quizzes".format(random.choice(wrong_category)))
                elif len(probable_categories) > 1:
                        print("I'm not sure which one you meant. Please specify again")
                        for w, v in probable_categories.items():
                                print(w, v)
                else:
                        category = list(probable_categories.keys())[0]
                        flag = True
        return category

def chooseDifficulty():
        difficulties = ['easy', 'medium', 'hard']
        flag = False
        difficulty = ""
        print('What difficulty level do you want?')
        while flag == False:
                user_response = input()
                if user_response.lower() in difficulties:
                        difficulty = user_response.lower()
                        flag = True
                else:
                        print('Oops! Please choose from easy, medium or hard')
        return difficulty

def loadQuestions(category, difficulty, num_questions):
        questions = []
        with open("./OpenTriviaQA_JSON/{}.json".format(category)) as f:
                data = json.load(f)
                for question in data['questions']:
                        if question['difficulty'] == difficulty:
                                questions.append(question)
                        if len(questions) == num_questions:
                                break
        return questions

def start(update, context):
    update.message.reply_text(random.choice(greeting))
    category = chooseCategory()
    difficulty = chooseDifficulty()
    num_questions = 5
    questions = loadQuestions(category, difficulty, num_questions)
    pprint(questions)
    context.user_data['questions'] = questions
    context.user_data['score'] = 0
    context.user_data['qnum'] = 0
    context.user_data['category'] = category
    context.user_data['difficulty'] = difficulty
    context.user_data['answered'] = False
    context.user_data['probable_choices'] = []

def next(update, context):
    score = context.user_data['score']
    questions = context.user_data['questions']
    qnum = context.user_data['qnum']
    probable_choices = context.user_data['probable_choices']
    if qnum == len(questions):
        update.message.reply_text("That's all for today! Your final score is {}".format(score))
        return
    if context.user_data['answered'] == False:
        update.message.reply_text('You need to answer the previous question first!')
        return
    context.user_data['answered'] = False
    question = questions[qnum]
    update.message.reply_text(random.choice(next_question))
    update.message.reply_text(question['question'])
    update.message.reply_text('a. ' + question['choices'][0])
    update.message.reply_text('b. ' + question['choices'][1])
    update.message.reply_text('c. ' + question['choices'][2])
    update.message.reply_text('d. ' + question['choices'][3])
    context.user_data['probable_choices'] = computeChoices(question['question'], question['choices'])
    context.user_data['qnum'] += 1

def answer(update, context):
    answer_choice = update.message.text.lower()
    probable_choices = context.user_data['probable_choices']
    if answer_choice not in ['a', 'b', 'c', 'd']:
        update.message.reply_text('Please select an answer from a, b, c, or d')
        return
    if answer_choice not in probable_choices:
        update.message.reply_text('Hmmm, I don\'t think that was an option')
        return
    questions = context.user_data['questions']
    qnum = context.user_data['qnum']
    question = questions[qnum - 1]
    if answer_choice == question['answer']:
        update.message.reply_text(random.choice(correct_answer))
        context.user_data['score'] = displayBotResponse(context.user_data['score'], correct_answer, True)
    else:
        update.message.reply_text(random.choice(wrong_answer))
        context.user_data['score'] = displayBotResponse(context.user_data['score'], wrong_answer, False, question['answer'])

    context.user_data['answered'] = True

def main():
    # Insert your Telegram bot token here
    TOKEN = "6135605220:AAGID1bjlBbWbV0DckTLW5WX0C_tOtWj_K8"
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # Add handlers for /start, /next, and answer commands
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("next", next))
    dp.add_handler(MessageHandler(Filters.regex('^(a|b|c|d)$'), answer))

    updater.start_polling()
    updater.idle()
