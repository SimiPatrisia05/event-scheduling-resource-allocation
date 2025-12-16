from flask import Flask, render_template, request, redirect, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///events.db'
app.config['SECRET_KEY'] = 'secret'
db = SQLAlchemy(app)

# ---------------- MODELS ---------------- #

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    description = db.Column(db.String(200))

class Resource(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    type = db.Column(db.String(50))

class Allocation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'))
    resource_id = db.Column(db.Integer, db.ForeignKey('resource.id'))

# ---------------- CONFLICT LOGIC ---------------- #

def has_conflict(resource_id, start, end, exclude_event_id=None):
    allocations = Allocation.query.filter_by(resource_id=resource_id).all()
    for alloc in allocations:
        event = Event.query.get(alloc.event_id)

        # Skip self when editing
        if exclude_event_id and event.id == exclude_event_id:
            continue

        if start < event.end_time and end > event.start_time:
            return True
    return False

# ---------------- ROUTES ---------------- #

@app.route('/')
def index():
    events = Event.query.all()
    resources = Resource.query.all()
    return render_template('index.html', events=events, resources=resources)

@app.route('/add_event', methods=['POST'])
def add_event():
    event = Event(
        title=request.form['title'],
        start_time=datetime.fromisoformat(request.form['start']),
        end_time=datetime.fromisoformat(request.form['end']),
        description=request.form['desc']
    )
    db.session.add(event)
    db.session.commit()
    return redirect('/')

@app.route('/add_resource', methods=['POST'])
def add_resource():
    resource = Resource(
        name=request.form['name'],
        type=request.form['type']
    )
    db.session.add(resource)
    db.session.commit()
    return redirect('/')

@app.route('/allocate', methods=['POST'])
def allocate():
    event_id = request.form['event']
    resource_id = request.form['resource']

    event = Event.query.get(event_id)

    if has_conflict(resource_id, event.start_time, event.end_time):
        flash("❌ Resource conflict detected!")
        return redirect('/')

    alloc = Allocation(event_id=event_id, resource_id=resource_id)
    db.session.add(alloc)
    db.session.commit()
    flash("✅ Resource allocated successfully!")
    return redirect('/')

# ---------------- EDIT EVENT ---------------- #

@app.route('/edit_event/<int:event_id>', methods=['GET', 'POST'])
def edit_event(event_id):
    event = Event.query.get(event_id)

    if request.method == 'POST':
        new_start = datetime.fromisoformat(request.form['start'])
        new_end = datetime.fromisoformat(request.form['end'])

        # Check conflicts for all allocated resources
        allocations = Allocation.query.filter_by(event_id=event.id).all()
        for alloc in allocations:
            if has_conflict(
                alloc.resource_id,
                new_start,
                new_end,
                exclude_event_id=event.id
            ):
                flash("❌ Conflict detected after editing event time!")
                return redirect('/')

        event.title = request.form['title']
        event.start_time = new_start
        event.end_time = new_end
        event.description = request.form['desc']

        db.session.commit()
        flash("✅ Event updated successfully!")
        return redirect('/')

    return render_template('edit_event.html', event=event)

# ---------------- REPORT ---------------- #

@app.route('/report')
def report():
    resources = Resource.query.all()
    data = []

    for r in resources:
        allocations = Allocation.query.filter_by(resource_id=r.id).all()
        total_hours = 0
        upcoming = []

        for a in allocations:
            e = Event.query.get(a.event_id)
            total_hours += (e.end_time - e.start_time).seconds / 3600
            upcoming.append(e.title)

        data.append({
            'name': r.name,
            'hours': total_hours,
            'upcoming': upcoming
        })

    return render_template('report.html', data=data)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
