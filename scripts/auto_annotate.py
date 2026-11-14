"""
scripts/auto_annotate.py
Auto-populates research/data/annotation_template.csv with 20 synthetic
booking turns, scoring detail_retention with the app's own phi_retain scorer.
Annotator-2 column left blank for human second-pass (Cohen's kappa step).
"""
import csv, sys, random
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from qpo.scoring import phi_retain

random.seed(1234)

TEMPLATES = [
    (['John Smith', '3 PM', 'deluxe room'],
     'Your booking is confirmed, John Smith. Deluxe room on Tuesday at 3 PM.'),
    (['Sarah', 'appointment', '2:30 PM', 'Dr. Patel'],
     'Sarah, your appointment with Dr. Patel is set for 2:30 PM tomorrow.'),
    (['checkout', '11 AM', 'room 204'],
     'Checkout for room 204 is at 11 AM. Is there anything else I can help with?'),
    (['pool access', 'included', 'sunrise package'],
     'Yes, pool access is included with the Sunrise Package.'),
    (['dinner reservation', '7:30 PM', 'Mr. Kumar', 'window table'],
     'Mr. Kumar, your dinner reservation is at 7:30 PM at a window table.'),
    (['cancel', 'appointment', 'Dr. Lee', 'Thursday'],
     'Your Thursday appointment with Dr. Lee has been cancelled.'),
    (['extra towels', 'room 310'],
     'I will send extra towels to room 310 right away.'),
    (['conference room B', '9 AM', 'Monday'],
     'Conference room B is booked for you on Monday at 9 AM.'),
    (['spa treatment', '4 PM', 'Ms. Priya'],
     'Ms. Priya, your spa treatment is confirmed for 4 PM today.'),
    (['medication reminder', 'blood pressure', 'Dr. Sharma'],
     'I have noted the blood pressure medication reminder. Dr. Sharma will be informed.'),
    (['suite upgrade', 'anniversary', 'complimentary'],
     'Happy anniversary! A complimentary suite upgrade has been arranged.'),
    (['late checkout', 'noon', 'room 517'],
     'Late checkout until noon has been approved for room 517.'),
    (['wheelchair', 'accessible room', 'ground floor'],
     'An accessible ground floor room with wheelchair access is reserved.'),
    (['breakfast', 'included', '7 AM', 'buffet'],
     'Breakfast buffet is included and runs from 7 AM. Enjoy your stay!'),
    (['follow-up', 'blood test', 'Thursday', '10 AM'],
     'Your blood test follow-up is scheduled for Thursday at 10 AM.'),
    (['parking', 'valet', 'complimentary'],
     'Complimentary valet parking is available for all our guests.'),
    (['room service', 'menu', '24 hours'],
     'Room service is available 24 hours. I will send the menu to your room.'),
    (['physiotherapy', '3 PM', 'Dr. Nair'],
     'Your physiotherapy session with Dr. Nair is confirmed at 3 PM.'),
    (['early checkin', '10 AM', 'ocean view'],
     'Early check-in at 10 AM for the ocean view room has been arranged.'),
    (['prescription', 'refill', 'pharmacy', '2 days'],
     'Prescription refill sent to pharmacy, ready in 2 days.'),
]

rows = []
for i, (gold_facts, response) in enumerate(TEMPLATES):
    score = phi_retain(response, gold_facts)
    ann1 = round(score * 2) / 2  # rounded to nearest 0.5
    rows.append({
        'turn_id': i + 1,
        'transcript': ' | '.join(gold_facts),
        'response': response,
        'detail_retention_gold': ', '.join(gold_facts),
        'detail_retention_annotator1': ann1,
        'detail_retention_annotator2': '',
        'notes': f'auto-scored phi_retain={score:.2f}; ann2 needed for kappa'
    })

out = Path('research/data/annotation_template.csv')
out.parent.mkdir(parents=True, exist_ok=True)
with open(out, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)

scores = [r['detail_retention_annotator1'] for r in rows]
print(f"Written {len(rows)} turns -> {out}")
print(f"Mean phi_retain (ann1): {sum(scores)/len(scores):.3f}")
for r in rows[:3]:
    print(f"  turn {r['turn_id']}: score={r['detail_retention_annotator1']}  facts={r['detail_retention_gold'][:45]}")

