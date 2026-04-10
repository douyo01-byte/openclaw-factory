import hashlib
import json
from datetime import datetime

ENGINE_VERSION = "fortune_engine_v1"

def _life_path_number(birth_date: str) -> int:
    digits = [int(c) for c in birth_date if c.isdigit()]
    n = sum(digits)
    while n > 9 and n not in (11, 22, 33):
        n = sum(int(c) for c in str(n))
    return n

def _name_number(name: str) -> int:
    n = sum(ord(c) for c in name.strip())
    while n > 9 and n not in (11, 22, 33):
        n = sum(int(c) for c in str(n))
    return n

def _seed(payload: dict) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def generate_reading(name: str, birth_date: str, question: str, birth_time: str = "", birth_place: str = "") -> dict:
    payload = {
        "name": name.strip(),
        "birth_date": birth_date.strip(),
        "birth_time": birth_time.strip(),
        "birth_place": birth_place.strip(),
        "question": question.strip(),
        "engine_version": ENGINE_VERSION,
    }
    input_hash = _seed(payload)
    life = _life_path_number(birth_date)
    name_no = _name_number(name)
    total = life + name_no
    while total > 9 and total not in (11, 22, 33):
        total = sum(int(c) for c in str(total))

    core_map = {
        1: "主体性が強く、自分で道を切り開く力が強い",
        2: "対人感覚が高く、相手との調和から運を引き上げやすい",
        3: "表現力が高く、発信や創作で流れを変えやすい",
        4: "積み上げ型で、継続と安定から結果を作りやすい",
        5: "変化対応が早く、環境の切り替えで運を動かしやすい",
        6: "責任感が強く、信頼構築が成果につながりやすい",
        7: "分析力が高く、深掘りで本質を見抜きやすい",
        8: "現実面に強く、収益化や結果化に向く",
        9: "視野が広く、全体最適で物事を整えやすい",
        11: "直感が鋭く、感覚の解像度が高い",
        22: "理想を仕組みに落とす力が強い",
        33: "人への影響力が大きく、支援で運が開きやすい",
    }

    advice_map = {
        1: "まず自分主導で決めることが重要です。",
        2: "相手の反応を観察して最適化すると精度が上がります。",
        3: "言語化と見せ方を整えるほど結果が安定します。",
        4: "短期よりも継続設計に寄せるほど強いです。",
        5: "動きながら修正する方が流れに乗れます。",
        6: "信頼を損なわない選択が最優先です。",
        7: "焦らず情報を集めるほど正答率が上がります。",
        8: "数字と現実条件を見て判断すると勝ちやすいです。",
        9: "目先より全体の整合性を優先すると良いです。",
        11: "直感は強いですが、確認を入れると再現性が上がります。",
        22: "大きな構想を小さな実行単位に落としてください。",
        33: "自分だけで抱えず、周囲への影響も考えると安定します。",
    }

    reading_text = "\n".join([
        f"鑑定エンジン: {ENGINE_VERSION}",
        f"基礎傾向: {core_map.get(total, core_map[7])}",
        f"今回の問い: {question.strip()}",
        f"判断軸: {advice_map.get(total, advice_map[7])}",
        "総合: 今回は勢いだけで動くより、条件を明文化してから進む方が結果が安定しやすい流れです。"
    ])

    output_hash = hashlib.sha256(reading_text.encode("utf-8")).hexdigest()

    return {
        "engine_version": ENGINE_VERSION,
        "input_hash": input_hash,
        "output_hash": output_hash,
        "life_path_number": life,
        "name_number": name_no,
        "master_number": total,
        "reading_text": reading_text,
        "consistency_score": 100,
        "generated_at": datetime.utcnow().isoformat(),
    }
