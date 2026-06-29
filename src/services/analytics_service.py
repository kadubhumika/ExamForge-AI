from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.models import User, Assignment, StudentSubmission, EvaluationResult, School


class AnalyticsService:

    @staticmethod
    def get_school_analytics(school_id: str, db: Session) -> Dict[str, Any]:
        school = db.query(School).filter(School.id == school_id).first()
        if not school:
            return {}

        teachers = db.query(User).filter(User.school_id == school_id).all()

        teacher_stats = []
        total_evaluations = 0

        for teacher in teachers:
            assignments = db.query(Assignment).filter(
                Assignment.teacher_id == teacher.id,
                Assignment.status == "DONE",
                Assignment.status != "DELETED"
            ).all()

            assignment_ids = [a.id for a in assignments]

            submissions = db.query(StudentSubmission).filter(
                StudentSubmission.assignment_id.in_(assignment_ids),
                StudentSubmission.status == "DONE"
            ).all()

            submission_ids = [s.id for s in submissions]
            total_evaluations += len(submission_ids)

            results = db.query(EvaluationResult).filter(
                EvaluationResult.submission_id.in_(submission_ids)
            ).all()

            avg_pct = 0.0
            if results:
                avg_pct = sum(r.percentage for r in results) / len(results)

            teacher_stats.append({
                "teacher_id": str(teacher.id),
                "teacher_name": teacher.name,
                "total_assignments": len(assignments),
                "total_students_evaluated": len(submission_ids),
                "average_marks_percentage": round(avg_pct, 1)
            })

        # Sort by average percentage descending
        teacher_stats.sort(key=lambda x: x["average_marks_percentage"], reverse=True)

        return {
            "school_name": school.name,
            "total_teachers": len(teachers),
            "total_assignments": sum(t["total_assignments"] for t in teacher_stats),
            "total_evaluations": total_evaluations,
            "teachers": teacher_stats
        }

    @staticmethod
    def get_teacher_analytics(teacher_id: str, db: Session) -> Dict[str, Any]:
        assignments = db.query(Assignment).filter(
            Assignment.teacher_id == teacher_id,
            Assignment.status == "DONE"
        ).order_by(Assignment.created_at.desc()).all()

        assignment_analytics = []
        for assignment in assignments:
            submissions = db.query(StudentSubmission).filter(
                StudentSubmission.assignment_id == assignment.id,
                StudentSubmission.status == "DONE"
            ).all()

            submission_ids = [s.id for s in submissions]
            results = db.query(EvaluationResult).filter(
                EvaluationResult.submission_id.in_(submission_ids)
            ).all()

            avg_pct = 0.0
            avg_marks = 0.0
            if results:
                avg_pct = sum(r.percentage for r in results) / len(results)
                avg_marks = sum(r.total_marks for r in results) / len(results)

            assignment_analytics.append({
                "assignment_id": str(assignment.id),
                "assignment_title": assignment.title,
                "total_students": len(submissions),
                "average_percentage": round(avg_pct, 1),
                "average_marks": round(avg_marks, 1),
                "created_at": assignment.created_at.isoformat()
            })

        return {
            "teacher_id": teacher_id,
            "assignments": assignment_analytics
        }