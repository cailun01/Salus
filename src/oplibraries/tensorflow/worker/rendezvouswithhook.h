/*
 * Copyright 2019 Peifeng Yu <peifeng@umich.edu>
 * 
 * This file is part of Salus
 * (see https://github.com/SymbioticLab/Salus).
 * 
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 * 
 *    http://www.apache.org/licenses/LICENSE-2.0
 * 
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#ifndef SALUS_OPLIB_TENSORFLOW_LOCALWRAPPERRENDEZVOUS_H
#define SALUS_OPLIB_TENSORFLOW_LOCALWRAPPERRENDEZVOUS_H

/*
 * Make sure tensorflow_headers is included first before
 * any other headers, so we can correctly override TF logging
 * with ours.
 */
#include "oplibraries/tensorflow/tensorflow_headers.h"
#include "utils/pointerutils.h"
#include <unordered_map>

/**
 * @brief Hook the rendez recv and send with device pointer
 */
class RendezvousWithHook : public tensorflow::Rendezvous
{
public:
    explicit RendezvousWithHook(std::shared_ptr<tensorflow::Device> device,
                                sstl::ScopedUnref<tensorflow::Rendezvous> localRendez);
    ~RendezvousWithHook() override;

    tensorflow::Status Send(const ParsedKey& parsed,
                            const Args& send_args,
                            const tensorflow::Tensor& val,
                            bool is_dead) override;

    void RecvAsync(const ParsedKey& parsed, const Args& recv_args, DoneCallback done) override;

    void StartAbort(const tensorflow::Status& status) override;

private:
    std::shared_ptr<tensorflow::Device> m_device;
    sstl::ScopedUnref<tensorflow::Rendezvous> m_local;
};

#endif // SALUS_OPLIB_TENSORFLOW_LOCALWRAPPERRENDEZVOUS_H
