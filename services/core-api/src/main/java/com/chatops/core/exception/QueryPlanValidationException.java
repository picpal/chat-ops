package com.chatops.core.exception;

import lombok.Getter;

@Getter
public class QueryPlanValidationException extends RuntimeException {

    private final String errorCode;
    private final String field;

    public QueryPlanValidationException(String message) {
        super(message);
        this.errorCode = "VALIDATION_ERROR";
        this.field = null;
    }

    public QueryPlanValidationException(String message, String field) {
        super(message);
        this.errorCode = "VALIDATION_ERROR";
        this.field = field;
    }

    public QueryPlanValidationException(String errorCode, String message, String field) {
        super(message);
        this.errorCode = errorCode;
        this.field = field;
    }
}
