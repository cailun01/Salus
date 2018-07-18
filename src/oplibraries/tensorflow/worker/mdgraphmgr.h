/*
 * <one line to give the library's name and an idea of what it does.>
 * Copyright (C) 2018  Peifeng Yu <peifeng@umich.edu>
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#ifndef SALUS_OPLIB_TENSORFLOW_MDGRAPHMGR_H
#define SALUS_OPLIB_TENSORFLOW_MDGRAPHMGR_H

#include "oplibraries/tensorflow/tensorflow_headers.h"

#include "execution/executionengine.h"
#include "oplibraries/tensorflow/worker/dummysessionmgr.h"
#include "utils/macros.h"

#include <memory>
#include <mutex>
#include <unordered_map>
#include <utility>

namespace salus::oplib::tensorflow {

/**
 * @brief MDGraphMgr keeps track of graph execution.
 *
 * Each computation graph is registered with MDGraphMgr. Then it is executed through it with multiple step_id.
 * This MDGraphMgr creates executor that is compatible with Salus internal execution engine.
 */
class MDGraphMgr : public tf::GraphMgr
{
public:
    explicit MDGraphMgr(const tf::WorkerEnv *env, std::shared_ptr<ExecutionContext> execCtx, ResStats rm);
    ~MDGraphMgr() override;

    Status Register(const std::string &session, const tf::GraphDef &gdef,
                    const tf::GraphOptions &graph_options, const tf::DebugOptions &debug_options,
                    tf::DistributedFunctionLibraryRuntime *cluster_flr, std::string *handle) override;

protected:
    struct MDItem : public Item
    {
        // Used to remove holds on devices' opsegment
        std::vector<tf::Device *> devices;

        ~MDItem() override;
    };

    tf::Status InitMDItem(const std::string &session, const tf::GraphDef &gdef,
                          const tf::GraphOptions &graph_options, const tf::DebugOptions &debug_options,
                          tf::DistributedFunctionLibraryRuntime *cluster_flr, MDItem *item);

private:
    std::shared_ptr<ExecutionContext> m_execCtx;

    ResStats m_rm;

    // Global Resource manager shared by all local devices.
    // NOTE: Must be valid when destorying opsegment, because
    // some op uses this during deconstruction.
    tf::ResourceMgr m_resourceMgr;

    // Global Opsegment shared by all local devices on all workers
    // (we have one and only one local worker)
    tf::OpSegment m_opseg;

    // Kernel to device name map
    std::unordered_map<const tf::OpKernel *, std::string> m_kernelToDevice;
    std::mutex m_mu;
};

CreateWorkerSessionFn GetCreateWorkerSessionFnForMDGraphMgr(const std::string &worker_name,
                                                            const tf::WorkerEnv *worker_env,
                                                            std::shared_ptr<ExecutionContext> execCtx,
                                                            const tf::ConfigProto &config);

} // namespace salus::oplib::tensorflow

#endif // SALUS_OPLIB_TENSORFLOW_MDGRAPHMGR_H
