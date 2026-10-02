from app.nodes import classify_question

test = classify_question({
    "question": "Who are the top 5 salespeople?"
})

print(test)

test_state = {
    "question": "Which salesperson generated the highest revenue?"
}

print(classify_question(test_state))