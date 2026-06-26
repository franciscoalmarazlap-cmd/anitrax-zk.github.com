pragma circom 2.0.0;

include "node_modules/circomlib/circuits/comparators.circom";

template Solvencia() {
    signal input saldo;
    signal input monto;
    signal output esValido;

    component lt = LessEqThan(64);
    lt.in[0] <== monto;
    lt.in[1] <== saldo;
    esValido <== lt.out;
}

component main {public [monto]} = Solvencia();