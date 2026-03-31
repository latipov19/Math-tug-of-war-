from flask import Blueprint, request, jsonify, g
from models import ScoreModel
from routes.auth import token_required
import datetime

lb_bp = Blueprint('leaderboard', __name__, url_prefix='/api/leaderboard')


def _serialize(rows: list) -> list:
    result = []
    for r in rows:
        row = dict(r)
        for k, v in row.items():
            if isinstance(v, (datetime.datetime, datetime.date)):
                row[k] = str(v)
        result.append(row)
    return result


@lb_bp.get('/')
def leaderboard():
    difficulty = request.args.get('difficulty')
    limit      = min(int(request.args.get('limit', 50)), 100)
    rows       = ScoreModel.get_leaderboard(difficulty, limit)
    return jsonify({'leaderboard': _serialize(rows)})


@lb_bp.get('/my-rank')
@token_required
def my_rank():
    rank = ScoreModel.get_user_rank(g.current_user['id'])
    return jsonify({'rank': rank, 'user_id': g.current_user['id']})
