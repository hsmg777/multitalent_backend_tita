from flask import request
from flask.views import MethodView
from flask_smorest import Blueprint, abort
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from ...ext.db import db
from ...models.admin.charges import Charges
from ...schemas.admin.charges import ChargesSchema

blp = Blueprint("Charges", __name__, description="CRUD de perfiles de cargo (charges) para cPanel")

def _require_admin():
    identity = get_jwt_identity()
    if not (isinstance(identity, str) and identity.startswith("admin:")):
        abort(403, message="Token no válido para cPanel")

list_schema = ChargesSchema(many=True)
item_schema = ChargesSchema()

def _paginate_query(query, page: int, per_page: int):
    total = query.count()
    items = (query.order_by(Charges.id.desc())
                  .offset((page - 1) * per_page)
                  .limit(per_page)
                  .all())
    return items, total

@blp.route("/")
class ChargesCollection(MethodView):
    @jwt_required()
    @blp.response(200)   
    def get(self):
        _require_admin()

        q = (request.args.get("q") or "").strip()
        area = (request.args.get("area") or "").strip()

        try:
            page = max(int(request.args.get("page", 1)), 1)
            per_page = max(min(int(request.args.get("per_page", 10)), 100), 1)
        except ValueError:
            abort(400, message="Parámetros de paginación inválidos")

        query = Charges.query
        if area:
            query = query.filter(Charges.area == area)
        if q:
            like = f"%{q.lower()}%"
            query = query.filter(or_(Charges.title.ilike(like),
                                     Charges.description.ilike(like)))

        items, total = _paginate_query(query, page, per_page)
        data = list_schema.dump(items)
        meta = {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page,
        }
        return {"items": data, "meta": meta}

    @jwt_required()
    @blp.arguments(ChargesSchema)
    @blp.response(201, ChargesSchema)
    def post(self, payload):
        _require_admin()
        charge = Charges(**payload)
        db.session.add(charge)
        try:
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            abort(400, message="Error de integridad al crear charge", extra=str(e))
        return charge

@blp.route("/<int:charge_id>")
class ChargesItem(MethodView):
    @jwt_required()
    @blp.response(200, ChargesSchema)
    def get(self, charge_id: int):
        _require_admin()
        return Charges.query.get_or_404(charge_id)

    @jwt_required()
    @blp.arguments(ChargesSchema)
    @blp.response(200, ChargesSchema)
    def put(self, payload, charge_id: int):
        _require_admin()
        charge = Charges.query.get_or_404(charge_id)
        charge.title = payload["title"]
        charge.area = payload.get("area")
        charge.description = payload["description"]
        try:
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            abort(400, message="Error de integridad al actualizar", extra=str(e))
        return charge

    @jwt_required()
    @blp.arguments(ChargesSchema(partial=True))
    @blp.response(200, ChargesSchema)
    def patch(self, payload, charge_id: int):
        _require_admin()
        charge = Charges.query.get_or_404(charge_id)
        for k, v in payload.items():
            setattr(charge, k, v)
        try:
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            abort(400, message="Error de integridad al actualizar", extra=str(e))
        return charge

    @blp.response(204)
    @jwt_required()
    def delete(self, charge_id: int):
        _require_admin()
        charge = Charges.query.get_or_404(charge_id)
        db.session.delete(charge)
        db.session.commit()
        return None
