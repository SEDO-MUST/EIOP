from django.contrib.auth.models import User
from django.db import transaction

from .models import (
    Enterprise,
    EnterpriseOwner,
    OrganizationAdministrator,
    Manager,
    Staff,
    Role,
    Permission,
)


@transaction.atomic
def create_eiop_user(
    *,
    user_type,
    name,
    email,
    username=None,
    password=None,
    phone_number=None,
    gender=None,
    date_of_birth=None,
    specialization=None,
    note=None,
    enterprise=None,
    role=None,
    permissions=None,
    field=None,
    direct_manager=None,
    rank=None,
):

    # ------------------------------------------------
    # BASIC USER INFORMATION
    # ------------------------------------------------

    if not username:
        username = email

    first_name = name
    last_name = ""

    # ------------------------------------------------
    # CREATE DJANGO USER
    # ------------------------------------------------

    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
    )

    # ------------------------------------------------
    # PERMISSIONS
    # ------------------------------------------------

    permission_objects = Permission.objects.filter(
        id__in=permissions or []
    )

    profile = None


    # =================================================
    # ORGANIZATION ADMINISTRATOR
    # =================================================

    if user_type == "ORG_ADMIN":

        profile = OrganizationAdministrator.objects.create(

            user=user,

            name=name,

            email=email,

            phoneNumber=phone_number or "",

            enterprise=enterprise,

            dateOfBirth=date_of_birth,

            gender=gender or "",

            specialization=specialization or "",

            note=note or "",

            role=role,

        )


    # =================================================
    # MANAGER
    # =================================================

    elif user_type == "MANAGER":

        profile = Manager.objects.create(

            user=user,

            name=name,

            email=email,

            phoneNumber=phone_number or "",

            enterprise=enterprise,

            dateOfBirth=date_of_birth,

            gender=gender or "",

            specialization=specialization or "",

            note=note,

            role=role,

            rank=rank or 1,

        )


        # Manager has extraPermissions
        profile.extraPermissions.set(
            permission_objects
        )


    # =================================================
    # STAFF
    # =================================================

    elif user_type == "STAFF":

        manager_object = None

        if direct_manager:

            manager_object = Manager.objects.filter(
                id=direct_manager,
                enterprise=enterprise,
                status="ACTIVE"
            ).first()


        profile = Staff.objects.create(

            user=user,

            name=name,

            email=email,

            phoneNumber=phone_number or "",

            enterprise=enterprise,

            dateOfBirth=date_of_birth,

            gender=gender or "",

            specialization=specialization or "",

            note=note or "",

            role=role,

            field=field or "",

            directManager=manager_object,

        )


        # Staff has extraPermissions
        profile.extraPermissions.set(
            permission_objects
        )


    # =================================================
    # INVALID USER TYPE
    # =================================================

    else:

        user.delete()

        raise ValueError(
            "Invalid EIOP user type."
        )


    return user, profile