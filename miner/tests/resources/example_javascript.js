import React from 'react';
import { useState, useEffect } from 'react';
const axios = require('axios');
const _ = require('lodash');

class Counter {
    constructor(initialValue) {
        this.value = initialValue;
    }

    increment() {
        this.value++;
    }

    decrement() {
        this.value--;
    }
}

function greet(name) {
    return `Hello, ${name}!`;
}

const add = (a, b) => a + b;

const multiply = function(a, b) {
    return a * b;
};

const fetchData = async (url) => {
    try {
        const response = await axios.get(url);
        return response.data;
    } catch (error) {
        console.error('Error fetching data:', error);
    }
};

function processArray(arr) {
    return _.map(arr, item => item * 2);
}

class UserManager {
    constructor() {
        this.users = [];
    }

    addUser(user) {
        this.users.push(user);
    }

    removeUser(userId) {
        this.users = this.users.filter(u => u.id !== userId);
    }

    getUser(userId) {
        return this.users.find(u => u.id === userId);
    }
}

export { Counter, greet, add, UserManager };
export default fetchData;
