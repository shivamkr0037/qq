import json
import random
import os
import nltk
from nltk.corpus import wordnet as wn
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import string
import telegram
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from telegram import ParseMode

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
                if sim >= 1:
                    probable_categories.clear()
                    probable_categories[w1] = w2
                    return probable_categories
                elif sim >= WUP_Threshold:
                    probable_categories[w1] = w2
    return probable_categories


# Compute the possible choices present in user_response
def computeChoices(user_response, choices):
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
        choice = nltk.word_tokenize(choice.lower())
        choice = [lemmatizer.lemmatize(word, pos='v') for word in choice]
        choice = [i for i in choice if i not in punctuations and i not in stop_words]
        choice = set(choice)
        if len(user_response.intersection(choice)) > 0:
            probable_choices.append(ct)
        ct = chr(ord(ct) + 1)
    return probable_choices


def displayBotResponse(score, responses, isCorrect, answer_choice=''):
    response = random.choice(responses)
    if isCorrect:
        score += 1
    else:
        score -= 0.25
        response += "\nThe correct answer is {}".format(answer_choice.upper())
    response += '\nScore = {}'.format(score)
    return score, response


def loadAllCategories():
    categories = set()
    for root, dirs, files in os.walk("./OpenTriviaQA_JSON"):
        for name in files:
            categories.add(name[:-5])
    return categories


def loadQuestions(category):
    if category is None:
        return None
    with open('./OpenTriviaQA_JSON/{}.json'.format(category)) as f:
        data = json.load(f)
    return data['results']


def start(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text=random.choice(greeting))


def quiz(update, context):
    categories = loadAllCategories()
    user_response = update.message.text
    if 'categories' in user_response.lower():
        context.bot.send_message(chat_id=update.effective_chat.id, text="Here are the categories available:\n{}".format('\n'.join(categories)))
        return
    if 'help' in user_response.lower():
        context.bot.send_message(chat_id=update.effective_chat.id, text="Type 'categories' to view all available categories, and type 'quiz /category' to start a quiz in that category")
        return
    category = user_response.split('/')
    if len(category) < 2:
        context.bot.send_message(chat_id=update.effective_chat.id, text='Please enter a valid category. Type \'help\' for help')
        return
    category = category[1]
    questions = loadQuestions(category)
    if questions is None:
        context.bot.send_message(chat_id=update.effective_chat.id, text=random.choice(wrong_category))
        return
    score, response = 0, ''
    for question in questions:
        response += random.choice(next_question) + '\n\n'
        response += question['question'] + '\n'
        choices = question['incorrect_answers']
        correct_choice = question['correct_answer']
        choices.append(correct_choice)
        random.shuffle(choices)
        response += '\n'.join(computeChoices(question['question'], choices)) + '\n'
        user_response = update.message.text
        user_response_NJ = extractNounsAndAdjectives(nltk.word_tokenize(user_response))
        probable_categories = computeCategories(set([category]), user_response_NJ)
        probable_choices = computeChoices(user_response, choices)
        isCorrect = False
        if correct_choice in probable_choices:
            isCorrect = True
        score, bot_response = displayBotResponse(score, correct_answer if isCorrect else wrong_answer, isCorrect, correct_choice)
        response += bot_response + '\n\n'
    context.bot.send_message(chat_id=update.effective_chat.id, text=response)


def main():
    token = os.environ.get('6135605220:AAGID1bjlBbWbV0DckTLW5WX0C_tOtWj_K8')
    updater = Updater(token, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", quiz))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, quiz))
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
