import os
import sys
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()


class Category(Base):

    __tablename__ = 'category'

    id = Column(Integer, primary_key=True)
    title = Column(String(50), nullable=False)

    @property
    def serialize(self):
        return {
            'id': self.id,
            'title': self.title

        }


class User(Base):

    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    username = Column(String(250))
    picture = Column(String(250))
    email = Column(String(250))


class Item(Base):

    __tablename__ = 'item'

    id = Column(Integer, primary_key=True)
    title = Column(String(50), nullable=True)
    description = Column(String(250))

    category_id = Column(Integer, ForeignKey('category.id'))
    category = relationship(Category)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)

    @property
    def serialize(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'cat_id': self.category.id
        }


engine = create_engine('sqlite:///catalogwithusers.db')
Base.metadata.create_all(engine)
