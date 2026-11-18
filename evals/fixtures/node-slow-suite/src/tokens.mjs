import {generateKeyPairSync,createSign,createVerify} from 'node:crypto';
export function newSigner(){const {privateKey,publicKey}=generateKeyPairSync('rsa',{modulusLength:2048});return {privateKey,publicKey};}
export const sign=(k,data)=>createSign('sha256').update(data).sign(k.privateKey,'base64');
export const verify=(k,data,sig)=>createVerify('sha256').update(data).verify(k.publicKey,sig,'base64');
