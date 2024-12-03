from flask import Flask, jsonify, request, Blueprint

app = Flask(__name__)

microservices = Blueprint('microservice', __name__)


def some_calculate_function(test):
    n = int(test['number_rows'])
    a = list(map(int, test['number_seats'].split()))
    k = int(test['number_visitors'])
    t = list(map(int, test['visitor_preferences'].split()))

    step_start = 0
    step_end = n - 1
    result = []
    for i in range(len(t)):
        if t[i] == 0:
            a[step_start] -= 1
            result.append(step_start + 1)
            if a[step_start] == 0:
                step_start += 1
        else:
            a[step_end] -= 1
            result.append(step_end + 1)
            if a[step_end] == 0:
                step_end -= 1

    return result


@app.route('/tests/calculate', methods=['POST'])
def calculate_result():
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        result = some_calculate_function(data)
        return jsonify({'result': result}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(port=5001)