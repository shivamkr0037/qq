import json
from random import choice
import os
import nltk
from nltk.corpus import wordnet as wn
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import string
import telegram
from telegram.ext import CommandHandler, MessageHandler, Filters, Updater

WUP_Threshold = 0.8
greeting = ['Hi there! Let\'s play a quiz!', 'Hello! Are you ready for a quiz?', 'Welcome to the quiz!']
wrong_category = ['Sorry, we don\'t have quizzes on that topic.', 'We don\'t have questions about that.']
next_question = ['Here comes the next question!', 'Get ready for the next one!', 'Here comes another question!']
correct_answer = ['Correct answer!', 'Well done!', 'You got it right!']
wrong_answer = ['Wrong answer. Keep trying!', 'Sorry, incorrect answer.', 'You missed it.']

def extractNounsAndAdjectives(words):
    NJ = []
    pos = nltk.pos_tag(words)
    for word, tag in pos:
        if tag[0] in ('N', 'J'):
            NJ.append(word)
    return NJ

def WUPSimilarity(w1, w2):
    w1 = wn.synsets(w1)
    w2 = wn.synsets(w2)
    max_WUP = 0
    for i in range(min(3, len(w1))):
        for j in range(min(3, len(w2))):
            sim = w1[i].wup_similarity(w2[j])
            if sim is not None:
                max_WUP = max(max_WUP, sim)
    return max_WUP

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
    print(choice(responses))
    if isCorrect:
        score += 1
    else:
        score -= 0.25
        print("The correct answer is {}".format(answer_choice.upper()))
    print('Score = {}'.format(score))
    return score

def loadAllCategories():
    categories = set()
    for root, dirs, files in os.walk("./OpenTriviaQA_JSON"):
            for name in files:
                categories.add(name[:-5])
    return categories

def chooseCategory():
    categories = loadAllCategories()
    category = choice(list(categories))
    return category

def chooseDifficulty():
    difficulties = ['easy', 'medium', 'hard']
    difficulty = choice(difficulties)
    return difficulty

def loadQuestions(category, difficulty, num_questions):
    questions = []
    with open(f"./OpenTriviaQA_JSON/{category}.json") as f:
        data = json.load(f)
        for question in data['questions']:
            if question['difficulty'] == difficulty:
                questions.append(question)
            if len(questions) == num_questions:
                break
    return questions

def start(update, context):
    update.message.reply_text(choice(greeting))
    category = chooseCategory()
    difficulty = chooseDifficulty()
    num_questions = 5
    questions = loadQuestions(category, difficulty, num_questions)
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
        update.message.reply_text(f"That's all for today! Your final score is {score}")
        return
    if context.user_data['answered'] == False:
        update.message.reply_text('You need to answer the previous question first!')
        return
    context.user_data['answered'] = False
    question = questions[qnum]
    update.message.reply_text(choice(next_question))
    update.message.reply_text(question['question'])
    for i, choice in enumerate(question['choices']):
        update.message.reply_text(f"{chr(ord('a')+i)}. {choice}")
    context.user_data['probable_choices'] = computeChoices(question['question'], question['choices'])
    context.user_data['qnum'] += 1

def answer(update, context):
    answer_choice = update.message.text.lower()
    probable_choices = context.user_data['probable_choices']
    if answer_choice not in ['a', 'b', 'c', 'd']:
        update.message.reply_text('Please select an answer from a, b, c, or d')
        return
    if answer_choice not in probable_choices:
        update.message.reply_text("Hmmm, I don't think that was an option")
        return
    questions = context.user_data['questions']
    qnum = context.user_data['qnum']
    question = questions[qnum - 1]
    if answer_choice == question['answer']:
        update.message.reply_text(choice(correct_answer))
        context.user_data['score'] = displayBotResponse(context.user_data['score'], correct_answer, True)
    else:
        update.message.reply_text(choice(wrong_answer))
        context.user_data['score'] = displayBotResponse(context.user_data['score'], wrong_answer, False, question['answer'])

    context.user_data['answered'] = True

def main():
    # Insert your Telegram bot token here
       TOKEN = "6135605220:AAGID1bjlBbWbV0DckTLW5WX0C_tOtWj_K8"
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("next", next))
    dp.add_handler(MessageHandler(Filters.regex('^(a|b|c|d)$'), answer))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
