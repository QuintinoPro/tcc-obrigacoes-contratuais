// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title ObligationRegistry
/// @notice Registro de rastreabilidade de obrigações contratuais.
/// Documentos e dados operacionais ficam off-chain; aqui ficam apenas hashes,
/// estados e eventos, o que permite verificar integridade e reconstruir o histórico.
contract ObligationRegistry {
    enum Status { Pendente, EmExecucao, Entregue, EmAnalise, Aprovado, Rejeitado, Concluido }

    struct Obligation {
        bytes32 contractHash; // SHA-256 do PDF do contrato
        bytes32 dataHash;     // SHA-256 dos dados validados da obrigação
        Status status;
        bool exists;
    }

    address public immutable operator;
    mapping(bytes32 => uint256) public contractRegisteredAt;
    mapping(uint256 => Obligation) public obligations;

    event ContractRegistered(bytes32 indexed contractHash, uint256 timestamp);
    event ObligationCreated(uint256 indexed obligationId, bytes32 indexed contractHash, bytes32 dataHash, uint256 timestamp);
    event StatusChanged(
        uint256 indexed obligationId,
        Status from,
        Status to,
        bytes32 evidenceHash,
        bytes32 actorRef,
        uint256 timestamp
    );

    error NotOperator();
    error AlreadyRegistered();
    error UnknownContract();
    error ObligationExists();
    error UnknownObligation();
    error InvalidTransition(Status from, Status to);

    modifier onlyOperator() {
        if (msg.sender != operator) revert NotOperator();
        _;
    }

    constructor() {
        operator = msg.sender;
    }

    function registerContract(bytes32 contractHash) external onlyOperator {
        if (contractRegisteredAt[contractHash] != 0) revert AlreadyRegistered();
        contractRegisteredAt[contractHash] = block.timestamp;
        emit ContractRegistered(contractHash, block.timestamp);
    }

    function createObligation(uint256 id, bytes32 contractHash, bytes32 dataHash) external onlyOperator {
        if (contractRegisteredAt[contractHash] == 0) revert UnknownContract();
        if (obligations[id].exists) revert ObligationExists();
        obligations[id] = Obligation(contractHash, dataHash, Status.Pendente, true);
        emit ObligationCreated(id, contractHash, dataHash, block.timestamp);
    }

    function transition(uint256 id, Status to, bytes32 evidenceHash, bytes32 actorRef) external onlyOperator {
        Obligation storage o = obligations[id];
        if (!o.exists) revert UnknownObligation();
        Status from = o.status;
        if (!isValidTransition(from, to)) revert InvalidTransition(from, to);
        o.status = to;
        emit StatusChanged(id, from, to, evidenceHash, actorRef, block.timestamp);
    }

    /// @notice Máquina de estados da obrigação (ver monografia, seção de arquitetura).
    function isValidTransition(Status f, Status t) public pure returns (bool) {
        if (f == Status.Pendente) return t == Status.EmExecucao;
        if (f == Status.EmExecucao) return t == Status.Entregue;
        if (f == Status.Entregue) return t == Status.EmAnalise;
        if (f == Status.EmAnalise) return t == Status.Aprovado || t == Status.Rejeitado;
        if (f == Status.Aprovado) return t == Status.Concluido;
        if (f == Status.Rejeitado) return t == Status.EmExecucao;
        return false;
    }
}
